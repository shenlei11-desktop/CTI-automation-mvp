"""Regex-based IOC (indicator of compromise) extraction.

Design notes
------------
Threat reports routinely *defang* indicators so they are not accidentally clickable
or resolvable: ``192[.]168[.]1[.]1``, ``hxxps://evil[.]com``, ``bad(.)domain``. A naive
regex that only matches clean indicators misses most real-world IOCs, so every pattern
here is defang-tolerant.

Crucially, we match indicators **in place** in the *original* text and normalize only
the matched substring. We do NOT rewrite the whole document first, because that would
shift every character offset and break the source-sentence provenance the rest of the
pipeline depends on. Each result therefore carries:

- ``value_raw``        — the indicator exactly as found (possibly defanged)
- ``value_normalized`` — the refanged / canonical form
- ``start`` / ``end``  — character span in the ORIGINAL text (valid for provenance)
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

from app.schemas.extraction import IOCType

# --- Defang building blocks -------------------------------------------------

# A "dot" separator as it appears defanged in the wild: . [.] (.) {.} [dot] (dot)
_DOT = r"(?:\[\.\]|\(\.\)|\{\.\}|\[[dD][oO][tT]\]|\([dD][oO][tT]\)|\.)"

# Zero-width space, ZWNJ, ZWJ, and BOM — sometimes inserted to break up indicators.
_ZERO_WIDTH = tuple(chr(cp) for cp in (0x200B, 0x200C, 0x200D, 0xFEFF))


def refang(value: str) -> str:
    """Convert a defanged indicator back to its canonical form."""
    v = value
    for zw in _ZERO_WIDTH:
        v = v.replace(zw, "")
    v = re.sub(r"h[xX]{2}p", "http", v)  # hxxp / hXXp -> http (keeps trailing 's')
    v = re.sub(r"\[[dD][oO][tT]\]|\([dD][oO][tT]\)", ".", v)
    v = v.replace("[.]", ".").replace("(.)", ".").replace("{.}", ".")
    v = v.replace("[:]", ":")
    return v


# --- Patterns ---------------------------------------------------------------

_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_TLD = r"[A-Za-z]{2,24}"

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
_SHA256_RE = re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{64}(?![A-Fa-f0-9])")
_SHA1_RE = re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{40}(?![A-Fa-f0-9])")
_MD5_RE = re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32}(?![A-Fa-f0-9])")
_IPV4_RE = re.compile(
    rf"(?<![\w.])(\d{{1,3}}{_DOT}\d{{1,3}}{_DOT}\d{{1,3}}{_DOT}\d{{1,3}})(?![\w.])"
)
_DOMAIN_RE = re.compile(rf"(?<![\w@.])((?:{_LABEL}{_DOT})+{_TLD})(?![A-Za-z0-9])")

# Common file extensions that look like domains (``report.pdf``, ``payload.exe``).
# Trade-off: a few of these (e.g. ``.zip``) are now real TLDs, so this can drop a
# genuine domain. In CTI text filenames vastly outnumber those, so we filter them;
# documented as a known limitation in the README.
_FILE_EXTENSIONS = {
    "exe", "dll", "sys", "bin", "bat", "ps1", "vbs", "jar", "apk", "msi",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf", "rtf", "txt", "log", "csv",
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "ico", "webp",
    "zip", "rar", "gz", "tar", "iso", "img", "dat", "tmp", "cfg", "ini",
}


@dataclass
class RawIOC:
    """An IOC before provenance is attached (see extraction.service)."""

    type: IOCType
    value_raw: str
    value_normalized: str
    start: int
    end: int
    is_private: bool | None = None


def _valid_ipv4(normalized: str) -> ipaddress.IPv4Address | None:
    try:
        return ipaddress.IPv4Address(normalized)
    except ValueError:
        return None


def extract_iocs(text: str) -> list[RawIOC]:
    """Extract deduplicated IOCs from ``text``, preserving original-text offsets."""
    claimed: list[tuple[int, int]] = []
    results: list[RawIOC] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= cs or start >= ce) for cs, ce in claimed)

    def add(ioc: RawIOC) -> None:
        claimed.append((ioc.start, ioc.end))
        results.append(ioc)

    # CVEs
    for m in _CVE_RE.finditer(text):
        add(RawIOC("cve", m.group(0), m.group(0).upper(), m.start(), m.end()))

    # Hashes: longest first so a 64-char SHA-256 is never split into shorter hashes.
    for ioc_type, pattern in (("sha256", _SHA256_RE), ("sha1", _SHA1_RE), ("md5", _MD5_RE)):
        for m in pattern.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            add(RawIOC(ioc_type, m.group(0), m.group(0).lower(), m.start(), m.end()))

    # IPv4 (octet-validated; private/reserved addresses are kept but tagged)
    for m in _IPV4_RE.finditer(text):
        if overlaps(m.start(1), m.end(1)):
            continue
        normalized = refang(m.group(1))
        addr = _valid_ipv4(normalized)
        if addr is None:
            continue
        add(
            RawIOC(
                "ipv4",
                m.group(1),
                normalized,
                m.start(1),
                m.end(1),
                is_private=addr.is_private or addr.is_reserved or addr.is_loopback,
            )
        )

    # Domains (filtering out filename look-alikes)
    for m in _DOMAIN_RE.finditer(text):
        if overlaps(m.start(1), m.end(1)):
            continue
        normalized = refang(m.group(1))
        tld = normalized.rsplit(".", 1)[-1].lower()
        if tld in _FILE_EXTENSIONS:
            continue
        add(RawIOC("domain", m.group(1), normalized, m.start(1), m.end(1)))

    # Deduplicate by (type, normalized value), keeping the first occurrence's span,
    # then return in document order for stable, readable output.
    seen: set[tuple[str, str]] = set()
    deduped: list[RawIOC] = []
    for ioc in sorted(results, key=lambda r: r.start):
        key = (ioc.type, ioc.value_normalized)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ioc)
    return deduped
