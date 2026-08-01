"""
Unit tests for vulnerability analyzer
"""

import pytest

from mcp_fuzzer.analyzer import VulnerabilityAnalyzer


class MockResult:
    """Mock MCP result object for testing"""

    def __init__(self, content: str):
        self.content = content


def test_analyze_command_injection():
    """Test detection of command injection indicators"""
    result = MockResult("root:x:0:0:root:/root:/bin/bash")

    is_vuln, reason = VulnerabilityAnalyzer.analyze_response(
        result, "; ls -la", "command_injection"
    )

    assert is_vuln is True
    assert "root:" in reason


def test_analyze_path_traversal():
    """Test detection of path traversal indicators"""
    result = MockResult("daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin")

    is_vuln, reason = VulnerabilityAnalyzer.analyze_response(
        result, "../../../etc/passwd", "path_traversal"
    )

    assert is_vuln is True


def test_analyze_sql_injection():
    """Test detection of SQL injection indicators"""
    result = MockResult("SQL syntax error near 'SELECT'")

    is_vuln, reason = VulnerabilityAnalyzer.analyze_response(
        result, "' OR '1'='1", "sql_injection"
    )

    assert is_vuln is True
    assert "sql syntax" in reason.lower()


def test_analyze_no_vulnerability():
    """Test that clean responses don't trigger false positives"""
    result = MockResult("File read successfully: Hello World")

    is_vuln, reason = VulnerabilityAnalyzer.analyze_response(
        result, "../../../etc/passwd", "path_traversal"
    )

    assert is_vuln is False
    assert reason is None


def test_get_severity():
    """Test severity scoring"""
    assert VulnerabilityAnalyzer.get_severity("command_injection") == "CRITICAL"
    assert VulnerabilityAnalyzer.get_severity("sql_injection") == "CRITICAL"
    assert VulnerabilityAnalyzer.get_severity("ssrf") == "CRITICAL"
    assert VulnerabilityAnalyzer.get_severity("path_traversal") == "HIGH"
    assert VulnerabilityAnalyzer.get_severity("xss") == "MEDIUM"


def test_get_remediation():
    """Test remediation advice"""
    remediation = VulnerabilityAnalyzer.get_remediation("command_injection")

    assert isinstance(remediation, str)
    assert len(remediation) > 0
    assert "parameter" in remediation.lower() or "input" in remediation.lower()


def test_get_cwe_id():
    """Test CWE ID mapping"""
    assert VulnerabilityAnalyzer.get_cwe_id("command_injection") == "CWE-78"
    assert VulnerabilityAnalyzer.get_cwe_id("path_traversal") == "CWE-22"
    assert VulnerabilityAnalyzer.get_cwe_id("sql_injection") == "CWE-89"
    assert VulnerabilityAnalyzer.get_cwe_id("ssrf") == "CWE-918"


def test_analyze_error():
    """Test error analysis"""
    error = Exception("SQL syntax error in query")

    is_vuln = VulnerabilityAnalyzer.analyze_error(
        error, "' OR '1'='1", "sql_injection"
    )

    assert is_vuln is True


def test_analyze_non_security_error():
    """Test that non-security errors aren't flagged"""
    error = Exception("Connection timeout")

    is_vuln = VulnerabilityAnalyzer.analyze_error(error, "test", "command_injection")

    # Connection timeout alone shouldn't be flagged as vulnerability
    assert is_vuln is False


def test_all_categories_have_remediations():
    """Test that all categories have remediation advice"""
    categories = [
        "command_injection",
        "path_traversal",
        "sql_injection",
        "prompt_injection",
        "ssrf",
        "xss",
    ]

    for category in categories:
        remediation = VulnerabilityAnalyzer.get_remediation(category)
        assert len(remediation) > 0, f"No remediation for {category}"
