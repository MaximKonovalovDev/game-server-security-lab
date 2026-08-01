"""
MCP Fuzzer - Runtime Security Testing for Model Context Protocol Servers

A comprehensive fuzzing tool for testing MCP servers against common
security vulnerabilities including command injection, path traversal,
SQL injection, SSRF, and prompt injection attacks.
"""

from .fuzzer import MCPFuzzer, FuzzingFinding
from .payloads import PayloadLibrary
from .analyzer import VulnerabilityAnalyzer

__version__ = "1.0.1"
__author__ = "Credence Security"

__all__ = [
    "MCPFuzzer",
    "FuzzingFinding",
    "PayloadLibrary",
    "VulnerabilityAnalyzer",
]
