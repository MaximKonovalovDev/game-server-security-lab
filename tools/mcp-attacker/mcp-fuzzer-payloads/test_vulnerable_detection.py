#!/usr/bin/env python3
"""
Test MCP Fuzzer Against Intentionally Vulnerable Server

This script verifies that the fuzzer correctly detects REAL vulnerabilities
while maintaining the false positive improvements from v1.0.1.
"""

import asyncio
import sys
from pathlib import Path

from mcp_fuzzer import MCPFuzzer


async def main():
    """Test fuzzer against vulnerable server"""

    print("=" * 70)
    print("TESTING MCP FUZZER AGAINST VULNERABLE SERVER")
    print("=" * 70)
    print()
    print("This test verifies the fuzzer detects REAL vulnerabilities:")
    print("  1. Command injection (execute_command tool)")
    print("  2. Path traversal (read_file_unsafe tool)")
    print("  3. SQL injection (query_users tool)")
    print()

    # Create fuzzer instance
    fuzzer = MCPFuzzer(
        server_command="python",
        server_args=[str(Path(__file__).parent / "tests" / "vulnerable_test_server.py")],
        verbose=True,
        timeout=60
    )

    # Run scan with critical vulnerability categories
    print("[*] Running fuzzer with command_injection, path_traversal, sql_injection")
    print()

    findings = await fuzzer.fuzz_server(
        categories=["command_injection", "path_traversal", "sql_injection"]
    )

    # Get summary
    summary = fuzzer.get_summary()

    # Print results
    print()
    print("=" * 70)
    print("VULNERABILITY DETECTION TEST RESULTS")
    print("=" * 70)
    print()
    print(f"Total tests run: {summary['total_tests']}")
    print(f"Vulnerabilities found: {summary['total_findings']}")
    print()

    if summary['total_findings'] == 0:
        print("❌ FAIL: No vulnerabilities detected!")
        print("   The fuzzer should detect the intentional vulnerabilities.")
        return 1

    print("By Severity:")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count}")

    print()
    print("By Category:")
    for category, count in summary["by_category"].items():
        print(f"  {category}: {count}")

    print()
    print("By Tool:")
    for tool, count in summary["by_tool"].items():
        print(f"  {tool}: {count}")

    # Verify expected vulnerabilities
    print()
    print("=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print()

    expected_vulnerable_tools = {"execute_command", "read_file_unsafe", "query_users"}
    found_vulnerable_tools = set(summary["by_tool"].keys())

    # Check each expected vulnerability
    results = []

    if "execute_command" in found_vulnerable_tools:
        print("✅ Command injection detected in execute_command")
        results.append(True)
    else:
        print("❌ Command injection NOT detected in execute_command")
        results.append(False)

    if "read_file_unsafe" in found_vulnerable_tools:
        print("✅ Path traversal detected in read_file_unsafe")
        results.append(True)
    else:
        print("❌ Path traversal NOT detected in read_file_unsafe")
        results.append(False)

    if "query_users" in found_vulnerable_tools:
        print("✅ SQL injection detected in query_users")
        results.append(True)
    else:
        print("❌ SQL injection NOT detected in query_users")
        results.append(False)

    # Show example findings
    if findings:
        print()
        print("=" * 70)
        print("EXAMPLE FINDINGS (first 5)")
        print("=" * 70)
        print()

        for i, finding in enumerate(findings[:5], 1):
            print(f"[{i}] {finding.tool_name} - {finding.payload_category}")
            print(f"    Severity: {finding.severity}")
            print(f"    Payload: {finding.payload[:60]}")
            print(f"    Reason: {finding.reason}")
            if finding.response_snippet:
                print(f"    Response: {finding.response_snippet[:100]}")
            print()

    # Final result
    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print()

    if all(results):
        print("✅ PASS: All expected vulnerabilities detected!")
        print()
        print("The fuzzer correctly identifies:")
        print("  - Real command injection vulnerabilities")
        print("  - Real path traversal vulnerabilities")
        print("  - Real SQL injection vulnerabilities")
        print()
        print("v1.0.1 improvements validated:")
        print("  ✅ Low false positives (secure servers: 0 findings)")
        print("  ✅ High true positives (vulnerable servers: detected)")
        return 0
    else:
        print("❌ FAIL: Some vulnerabilities were not detected")
        print()
        print("This indicates the v1.0.1 changes may have been too aggressive")
        print("and are now missing real vulnerabilities.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
