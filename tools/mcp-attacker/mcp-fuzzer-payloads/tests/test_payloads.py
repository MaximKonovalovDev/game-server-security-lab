"""
Unit tests for payload library
"""

import pytest

from mcp_fuzzer.payloads import PayloadLibrary


def test_get_all_payloads():
    """Test getting all payload categories"""
    payloads = PayloadLibrary.get_all_payloads()

    assert isinstance(payloads, dict)
    assert len(payloads) > 0
    assert "command_injection" in payloads
    assert "path_traversal" in payloads
    assert "sql_injection" in payloads


def test_get_category():
    """Test getting specific category"""
    cmd_payloads = PayloadLibrary.get_category("command_injection")

    assert isinstance(cmd_payloads, list)
    assert len(cmd_payloads) > 0
    assert any("; ls" in p for p in cmd_payloads)


def test_get_nonexistent_category():
    """Test getting non-existent category returns empty list"""
    payloads = PayloadLibrary.get_category("nonexistent_category")

    assert payloads == []


def test_get_total_count():
    """Test total payload count"""
    total = PayloadLibrary.get_total_count()

    assert total > 100  # Should have at least 100 payloads
    assert isinstance(total, int)


def test_command_injection_payloads():
    """Test command injection payloads are present"""
    payloads = PayloadLibrary.COMMAND_INJECTION

    assert len(payloads) > 0
    assert "; ls -la" in payloads
    assert "| cat /etc/passwd" in payloads
    assert "$(whoami)" in payloads


def test_path_traversal_payloads():
    """Test path traversal payloads are present"""
    payloads = PayloadLibrary.PATH_TRAVERSAL

    assert len(payloads) > 0
    assert "../../../etc/passwd" in payloads
    assert any("windows" in p.lower() for p in payloads)


def test_sql_injection_payloads():
    """Test SQL injection payloads are present"""
    payloads = PayloadLibrary.SQL_INJECTION

    assert len(payloads) > 0
    assert "' OR '1'='1" in payloads
    assert any("DROP TABLE" in p for p in payloads)


def test_prompt_injection_payloads():
    """Test prompt injection payloads are present"""
    payloads = PayloadLibrary.PROMPT_INJECTION

    assert len(payloads) > 0
    assert any("Ignore previous" in p for p in payloads)
    assert any("SYSTEM" in p for p in payloads)


def test_all_categories_have_payloads():
    """Test that all categories have at least one payload"""
    all_payloads = PayloadLibrary.get_all_payloads()

    for category, payloads in all_payloads.items():
        assert len(payloads) > 0, f"Category {category} has no payloads"
        assert isinstance(payloads, list), f"Category {category} payloads is not a list"
