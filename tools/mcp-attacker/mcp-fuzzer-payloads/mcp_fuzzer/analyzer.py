"""
Vulnerability Analysis Module

Analyzes MCP server responses to detect vulnerability indicators.
"""

from typing import Any, Dict, List, Optional


class VulnerabilityAnalyzer:
    """Analyzes tool responses to detect security vulnerabilities"""

    # Indicators that security controls are WORKING (not vulnerable)
    SECURITY_CONTROL_INDICATORS = [
        "access denied",
        "permission denied",
        "unauthorized",
        "forbidden",
        "not allowed",
        "outside allowed",
        "blocked",
        "rejected",
        "invalid path",
        "restricted",
        "cannot access",  # Often means controls working
        "not permitted",
        "security violation",
        "policy violation",
    ]

    # Vulnerability indicators by category - ONLY successful exploitation
    INDICATORS = {
        "command_injection": [
            "root:x:",  # /etc/passwd content
            "uid=",  # Command output showing user ID (more flexible)
            "drwx",  # Directory listing output (any permissions)
            "bin/bash",  # Shell output
            "bin/sh",  # Shell output
            "nobody:x:",  # Password file content
            "total ",  # ls -la output (with space to be specific)
        ],
        "path_traversal": [
            "root:x:0:0",  # /etc/passwd content
            "daemon:x:",  # /etc/passwd content
            "[boot loader]",  # Windows boot.ini
            "c:\\windows\\system32",  # Windows system path in actual content
            "localhost",  # /etc/hosts content
            "127.0.0.1",  # /etc/hosts content
        ],
        "sql_injection": [
            "sql syntax",
            "mysql_",
            "ora-",
            "sqlite_error",
            "pg_query",
            "you have an error in your sql",
            "warning: mysql",
            "sqlstate",
            "syntax error at or near",
            "unclosed quotation mark",
            "sql query executed",  # Successful query execution logs
            "select * from",  # SQL query in response
            "password:",  # Database field leaked
            "secret",  # Password/secret leaked
        ],
        "ssrf": [
            "ami-id",
            "instance-id",
            "metadata",
            "computemetadata",
            "iam/security-credentials",
            "iam-info",
            "placement/availability",
            "instance-identity",
        ],
        "prompt_injection": [
            "developer mode",
            "system:",
            "ignoring previous",
            "new instructions",
            "override",
            "admin mode",
            "unrestricted",
            "safety protocols",
        ],
        "xss": [
            "<script",
            "onerror=",
            "javascript:",
            "alert(",
            "eval(",
            "onload=",
            "<iframe",
        ],
        "ldap_injection": [
            "ldap_search",
            "invalid dn syntax",
            "ldap error",
        ],
        "xml_injection": [
            "<?xml",
            "<!doctype",
            "<!entity",
            "parser error",
            "xml declaration",
        ],
        "nosql_injection": [
            "mongodb",
            "parseerror",
            "$where",
            "bson",
        ],
        "template_injection": [
            "jinja2",
            "templateerror",
            "render error",
            "__mro__",
            "subclasses",
        ],
    }

    # Generic error indicators
    ERROR_INDICATORS = [
        "error",
        "exception",
        "stack trace",
        "traceback",
        "warning",
        "failed",
        "denied",
        "fatal",
        "critical",
        "unexpected",
    ]

    # Severity scoring
    SEVERITY_SCORES = {
        "command_injection": "CRITICAL",
        "sql_injection": "CRITICAL",
        "ssrf": "CRITICAL",
        "path_traversal": "HIGH",
        "prompt_injection": "HIGH",
        "xml_injection": "HIGH",
        "nosql_injection": "HIGH",
        "xss": "MEDIUM",
        "ldap_injection": "MEDIUM",
        "template_injection": "HIGH",
        "crlf_injection": "MEDIUM",
        "null_bytes": "MEDIUM",
        "integer_overflow": "MEDIUM",
        "format_string": "MEDIUM",
    }

    @classmethod
    def analyze_response(
        cls, result: Any, payload: str, category: str
    ) -> tuple[bool, Optional[str]]:
        """
        Analyze tool response to detect vulnerabilities

        Args:
            result: MCP tool response object
            payload: The payload that was sent
            category: Payload category (e.g., "command_injection")

        Returns:
            Tuple of (is_vulnerable, reason)
        """
        if not hasattr(result, "content"):
            return False, None

        content_str = str(result.content).lower()

        # FIRST: Check if security controls are working
        # If we see these indicators, the attack was BLOCKED (not vulnerable)
        for control_indicator in cls.SECURITY_CONTROL_INDICATORS:
            if control_indicator in content_str:
                # Security control is working - not vulnerable
                return False, None

        # Check for category-specific SUCCESS indicators
        category_indicators = cls.INDICATORS.get(category, [])

        for indicator in category_indicators:
            if indicator.lower() in content_str:
                return True, f"Response contains '{indicator}' - successful {category}"

        # Only flag errors if they indicate PROCESSING issues, not access control
        # Skip the generic "error + payload" check as it causes too many false positives

        return False, None

    @classmethod
    def get_severity(cls, category: str) -> str:
        """Get severity level for vulnerability category"""
        return cls.SEVERITY_SCORES.get(category, "LOW")

    @classmethod
    def analyze_error(cls, error: Exception, payload: str, category: str) -> bool:
        """
        Analyze exception to determine if it indicates a vulnerability

        Args:
            error: Exception that was raised
            payload: The payload that caused the error
            category: Payload category

        Returns:
            True if error indicates vulnerability
        """
        error_str = str(error).lower()

        # FIRST: Check if this is a security control working correctly
        # These errors mean the server REJECTED the attack (good)
        for control_indicator in cls.SECURITY_CONTROL_INDICATORS:
            if control_indicator in error_str:
                return False  # Not vulnerable - security control working

        # Only flag errors that indicate PROCESSING vulnerabilities
        # (not access control rejections)
        processing_error_patterns = [
            "syntax error",  # SQL/code parsing errors
            "sql",  # SQL errors (not access control)
            "parse error",  # Parsing issues
            "malformed",  # Malformed input processed
            "unexpected",  # Unexpected behavior
            "stack trace",  # Application errors
            "exception",  # Unhandled exceptions
        ]

        return any(pattern in error_str for pattern in processing_error_patterns)

    @classmethod
    def get_remediation(cls, category: str) -> str:
        """Get remediation advice for vulnerability type"""
        remediations = {
            "command_injection": "Use parameterized commands. Never use shell=True. Implement strict input validation and sanitization.",
            "path_traversal": "Implement path canonicalization and allowlisting. Reject paths containing '..' or absolute paths. Use chroot/jail environments.",
            "sql_injection": "Use prepared statements with parameterized queries. Never concatenate user input into SQL. Use ORM frameworks.",
            "prompt_injection": "Implement input sanitization and output filtering. Use structured prompts. Separate user content from system instructions.",
            "ssrf": "Implement strict allowlist for external requests. Validate and sanitize URLs. Block access to internal IP ranges.",
            "xss": "Sanitize user input and escape output. Use Content Security Policy headers. Validate against allowlist of safe characters.",
            "ldap_injection": "Use parameterized queries. Escape special LDAP characters. Implement strict input validation.",
            "xml_injection": "Disable external entity processing. Use safe XML parsers. Validate XML against schema.",
            "nosql_injection": "Use parameterized queries. Validate input types. Implement strict schema validation.",
            "template_injection": "Use sandboxed template engines. Avoid eval() and exec(). Validate template syntax.",
            "crlf_injection": "Sanitize newline characters from user input. Use HTTP libraries that auto-encode headers.",
            "null_bytes": "Reject inputs containing null bytes. Validate file extensions separately from names.",
            "integer_overflow": "Implement bounds checking. Use appropriate integer types. Validate numeric inputs.",
            "format_string": "Never use user input directly in format strings. Use safe formatting methods.",
        }

        return remediations.get(
            category, "Review input validation and implement appropriate security controls."
        )

    @classmethod
    def get_cwe_id(cls, category: str) -> Optional[str]:
        """Get CWE ID for vulnerability category"""
        cwe_mapping = {
            "command_injection": "CWE-78",
            "path_traversal": "CWE-22",
            "sql_injection": "CWE-89",
            "prompt_injection": "CWE-77",  # Command injection variant
            "ssrf": "CWE-918",
            "xss": "CWE-79",
            "ldap_injection": "CWE-90",
            "xml_injection": "CWE-611",
            "nosql_injection": "CWE-943",
            "crlf_injection": "CWE-93",
            "integer_overflow": "CWE-190",
            "format_string": "CWE-134",
        }

        return cwe_mapping.get(category)
