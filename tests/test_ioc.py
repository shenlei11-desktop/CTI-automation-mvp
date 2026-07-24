"""Unit tests for defang-aware IOC extraction (no spaCy model required)."""

from __future__ import annotations

from app.extraction.ioc import extract_iocs, refang


def _by_type(iocs, ioc_type):
    return [i for i in iocs if i.type == ioc_type]


def test_refang():
    assert refang("185[.]220[.]101[.]45") == "185.220.101.45"
    assert refang("hxxps://update-modicon[.]net") == "https://update-modicon.net"
    assert refang("evil(.)com") == "evil.com"
    assert refang("bad[dot]domain") == "bad.domain"


def test_defanged_public_ip_offsets_and_flag():
    text = "beaconing to 185[.]220[.]101[.]45 over port 443"
    ips = _by_type(extract_iocs(text), "ipv4")
    assert len(ips) == 1
    ip = ips[0]
    assert ip.value_normalized == "185.220.101.45"
    assert ip.is_private is False
    # Offsets must index the ORIGINAL (still-defanged) text — this is what keeps
    # provenance valid.
    assert text[ip.start : ip.end] == ip.value_raw == "185[.]220[.]101[.]45"


def test_private_ip_flagged():
    ips = _by_type(extract_iocs("lateral movement to 10[.]0[.]0[.]5 internally"), "ipv4")
    assert ips and ips[0].is_private is True


def test_domain_from_defanged_url():
    iocs = extract_iocs("staging from hxxps://update-modicon[.]net/payload.bin")
    assert any(d.value_normalized == "update-modicon.net" for d in _by_type(iocs, "domain"))


def test_all_hash_types():
    sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    types = {i.type for i in extract_iocs(f"iocs: {sha256} {sha1} {md5}")}
    assert {"sha256", "sha1", "md5"} <= types


def test_cve_normalized_uppercase():
    cves = _by_type(extract_iocs("tracked as cve-2026-2841 today"), "cve")
    assert cves and cves[0].value_normalized == "CVE-2026-2841"


def test_version_string_is_not_ip():
    assert _by_type(extract_iocs("running version 1.2.3 of the tool"), "ipv4") == []


def test_filenames_are_not_domains():
    assert _by_type(extract_iocs("see report.pdf and payload.exe attached"), "domain") == []


def test_dedup_keeps_single_entry():
    iocs = extract_iocs("CVE-2026-2841 ... again CVE-2026-2841 here")
    assert len(_by_type(iocs, "cve")) == 1
