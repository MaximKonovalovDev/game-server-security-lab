"""
MCP Fuzzer Core Module

Runtime security testing for Model Context Protocol servers.
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .analyzer import VulnerabilityAnalyzer
from .payloads import PayloadLibrary


@dataclass
class FuzzingFinding:
    """Result from fuzzing a single tool parameter"""

    tool_name: str
    parameter: str
    payload: str
    payload_category: str
    vulnerability_detected: bool
    severity: str
    response_snippet: str = ""
    error: Optional[str] = None
    reason: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MCPFuzzer:
    """
    Production MCP fuzzer using the official MCP SDK
    Tests runtime behavior with malicious inputs
    """

    def __init__(
        self,
        server_command: str,
        server_args: Optional[List[str]] = None,
        timeout: int = 300,
        max_payload_length: int = 1000,
        verbose: bool = False,
    ):
        """
        Initialize MCP Fuzzer

        Args:
            server_command: Command to start MCP server (e.g., "npx" or "python")
            server_args: Arguments for server command (e.g., ["-y", "@modelcontextprotocol/server-filesystem", "/path"])
            timeout: Overall fuzzing timeout in seconds
            max_payload_length: Maximum length of payloads to test
            verbose: Enable verbose output
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.timeout = timeout
        self.max_payload_length = max_payload_length
        self.verbose = verbose
        self.findings: List[FuzzingFinding] = []
        self.total_tests = 0
        self.start_time = None

    async def fuzz_server(
        self, categories: Optional[List[str]] = None
    ) -> List[FuzzingFinding]:
        """
        Main entry point - fuzz all tools on the MCP server

        Args:
            categories: List of payload categories to test. If None, tests all categories.

        Returns:
            List of vulnerability findings
        """
        self.start_time = datetime.utcnow()
        self.findings = []
        self.total_tests = 0

        if self.verbose:
            print(f"[*] Starting MCP Fuzzer")
            print(f"[*] Command: {self.server_command} {' '.join(self.server_args)}")

        try:
            # Prepare environment with nvm PATH for npx
            env = os.environ.copy()

            # Add nvm bin directory to PATH if it exists
            nvm_dir = os.path.expanduser("~/.nvm")
            if os.path.exists(nvm_dir):
                # Find the current node version directory
                versions_dir = os.path.join(nvm_dir, "versions", "node")
                if os.path.exists(versions_dir):
                    # Get the most recent version (or first available)
                    node_versions = sorted(os.listdir(versions_dir))
                    if node_versions:
                        node_bin = os.path.join(versions_dir, node_versions[-1], "bin")
                        if os.path.exists(node_bin):
                            env['PATH'] = f"{node_bin}:{env.get('PATH', '')}"
                            if self.verbose:
                                print(f"[*] Added to PATH: {node_bin}")

            # Connect to MCP server
            async with stdio_client(
                StdioServerParameters(
                    command=self.server_command, args=self.server_args, env=env
                )
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()
                    if self.verbose:
                        print("[+] MCP session initialized")

                    # Enumerate available tools
                    tools_response = await session.list_tools()
                    tools = tools_response.tools

                    if self.verbose:
                        print(f"[*] Found {len(tools)} tools to fuzz")
                        for tool in tools:
                            print(f"    - {tool.name}")

                    # Fuzz each tool
                    for tool in tools:
                        await self._fuzz_tool(session, tool, categories)

        except Exception as e:
            print(f"[!] Fatal error during fuzzing: {e}")
            if self.verbose:
                import traceback

                traceback.print_exc()

        # Print summary
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        if self.verbose:
            print(f"\n[*] Fuzzing complete in {elapsed:.2f}s")
            print(f"[*] Total tests: {self.total_tests}")
            print(f"[*] Vulnerabilities found: {len(self.findings)}")

        return self.findings

    async def _fuzz_tool(
        self, session: ClientSession, tool: Any, categories: Optional[List[str]] = None
    ):
        """Fuzz a single tool with all payload categories"""

        if self.verbose:
            print(f"\n[*] Fuzzing tool: {tool.name}")

        if not tool.inputSchema:
            if self.verbose:
                print(f"    ⚠️  No input schema defined, skipping")
            return

        parameters = tool.inputSchema.get("properties", {})

        if not parameters:
            if self.verbose:
                print(f"    ⚠️  No parameters defined, skipping")
            return

        # Get payload categories to test
        all_payloads = PayloadLibrary.get_all_payloads()
        if categories:
            payloads_to_test = {
                k: v for k, v in all_payloads.items() if k in categories
            }
        else:
            payloads_to_test = all_payloads

        # Test each parameter with each payload category
        for param_name, param_schema in parameters.items():
            param_type = param_schema.get("type", "string")

            if self.verbose:
                print(f"    Testing parameter: {param_name} ({param_type})")

            for category, payloads in payloads_to_test.items():
                for payload in payloads:
                    # Skip payloads that are too long
                    if len(str(payload)) > self.max_payload_length:
                        continue

                    # Skip payloads that don't match parameter type
                    if not self._payload_matches_type(payload, param_type):
                        continue

                    self.total_tests += 1

                    try:
                        # Build test parameters
                        test_params = self._build_test_params(
                            parameters, param_name, payload
                        )

                        # Call tool with malicious payload
                        result = await asyncio.wait_for(
                            session.call_tool(tool.name, test_params),
                            timeout=10,  # Per-call timeout
                        )

                        # Analyze response for vulnerability indicators
                        is_vulnerable, reason = VulnerabilityAnalyzer.analyze_response(
                            result, payload, category
                        )

                        if is_vulnerable:
                            finding = FuzzingFinding(
                                tool_name=tool.name,
                                parameter=param_name,
                                payload=str(payload)[:200],
                                payload_category=category,
                                vulnerability_detected=True,
                                severity=VulnerabilityAnalyzer.get_severity(category),
                                response_snippet=str(result.content)[:500],
                                reason=reason,
                                remediation=VulnerabilityAnalyzer.get_remediation(
                                    category
                                ),
                                cwe_id=VulnerabilityAnalyzer.get_cwe_id(category),
                            )
                            self.findings.append(finding)

                            if self.verbose:
                                print(
                                    f"      🚨 VULNERABLE: {category} ({finding.severity})"
                                )
                                print(f"         Reason: {reason}")

                    except asyncio.TimeoutError:
                        # Timeout might indicate DoS vulnerability
                        finding = FuzzingFinding(
                            tool_name=tool.name,
                            parameter=param_name,
                            payload=str(payload)[:200],
                            payload_category="timeout_dos",
                            vulnerability_detected=True,
                            severity="MEDIUM",
                            response_snippet="",
                            error="Request timed out - possible DoS",
                            reason="Tool call exceeded timeout threshold",
                            remediation="Implement request timeout limits and resource constraints",
                            cwe_id="CWE-400",
                        )
                        self.findings.append(finding)

                        if self.verbose:
                            print(f"      🚨 TIMEOUT: Possible DoS (MEDIUM)")

                    except Exception as e:
                        # Analyze if error indicates vulnerability
                        if VulnerabilityAnalyzer.analyze_error(e, payload, category):
                            finding = FuzzingFinding(
                                tool_name=tool.name,
                                parameter=param_name,
                                payload=str(payload)[:200],
                                payload_category=category,
                                vulnerability_detected=True,
                                severity=VulnerabilityAnalyzer.get_severity(category),
                                response_snippet="",
                                error=str(e)[:500],
                                reason=f"Error response indicates {category}",
                                remediation=VulnerabilityAnalyzer.get_remediation(
                                    category
                                ),
                                cwe_id=VulnerabilityAnalyzer.get_cwe_id(category),
                            )
                            self.findings.append(finding)

                            if self.verbose:
                                print(
                                    f"      🚨 ERROR: {category} ({finding.severity})"
                                )
                                print(f"         {str(e)[:100]}")

    def _payload_matches_type(self, payload: Any, param_type: str) -> bool:
        """Check if payload is appropriate for parameter type"""

        if param_type == "string":
            return True
        elif param_type in ["number", "integer"] and isinstance(payload, (int, float)):
            return True
        elif param_type == "array" and isinstance(payload, list):
            return True
        elif param_type == "object" and isinstance(payload, dict):
            return True

        # Try to coerce string payloads for other types
        return isinstance(payload, str)

    def _build_test_params(
        self, parameters: Dict, target_param: str, payload: Any
    ) -> Dict:
        """Build parameter dict with malicious payload"""

        params = {}

        for param_name, param_schema in parameters.items():
            if param_name == target_param:
                # Inject malicious payload
                params[param_name] = payload
            else:
                # Use safe default values for other parameters
                param_type = param_schema.get("type", "string")

                # Check if parameter is required
                # If not required, we can skip it to minimize side effects
                # For now, provide defaults for all params
                params[param_name] = self._get_default_value(param_type)

        return params

    def _get_default_value(self, param_type: str) -> Any:
        """Get safe default value for parameter type"""

        defaults = {
            "string": "test",
            "number": 1,
            "integer": 1,
            "boolean": True,
            "array": [],
            "object": {},
        }

        return defaults.get(param_type, "test")

    def get_summary(self) -> Dict:
        """Get summary statistics of fuzzing results"""

        # Count by severity
        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

        for finding in self.findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

        # Count by category
        by_category = {}
        for finding in self.findings:
            cat = finding.payload_category
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by tool
        by_tool = {}
        for finding in self.findings:
            tool = finding.tool_name
            by_tool[tool] = by_tool.get(tool, 0) + 1

        elapsed = None
        if self.start_time:
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "total_tests": self.total_tests,
            "total_findings": len(self.findings),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_tool": by_tool,
            "elapsed_seconds": elapsed,
        }
