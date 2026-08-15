"""Unit tests for HTML -> text extraction (pure function, no network)."""

from __future__ import annotations

from app.ingestion.html_extract import extract_text_from_html

_SAMPLE_HTML = """
<html><head><title>ICSA-26-999-01: Fake Vendor PLC Vulnerability</title></head>
<body>
<nav>Home | Advisories | Contact</nav>
<article>
<h1>ICSA-26-999-01: Fake Vendor PLC Vulnerability</h1>
<p>EXECUTIVE SUMMARY</p>
<p>CVSS v3.1 base score of 9.8 has been calculated. The vulnerability affects
internet-facing devices used in safety-critical process control.</p>
<p>Attributed to VOLTZITE targeting Fake Vendor Modicon controllers.</p>
</article>
<footer>Copyright 2026 CISA. All rights reserved.</footer>
</body></html>
"""


def test_extract_text_from_html_strips_boilerplate():
    result = extract_text_from_html(_SAMPLE_HTML)
    assert "CVSS v3.1 base score of 9.8" in result.text
    assert "VOLTZITE" in result.text
    # Nav and footer boilerplate should not survive.
    assert "Contact" not in result.text
    assert "Copyright" not in result.text


def test_extract_text_from_html_captures_title():
    result = extract_text_from_html(_SAMPLE_HTML)
    assert result.title == "ICSA-26-999-01: Fake Vendor PLC Vulnerability"


def test_extract_text_from_html_empty_input_returns_empty_result():
    result = extract_text_from_html("<html><body></body></html>")
    assert result.text == ""
    assert result.title is None
