#!/usr/bin/env python3
"""
Quick MCP Server Scanner

Simple script to scan an MCP server with the standalone MCP Fuzzer.
This demonstrates the fuzzer working independently of the full DAST pipeline.

Usage:
    python scan_mcp_server.py
"""

import asyncio
import sys
from mcp_fuzzer import MCPFuzzer


async def main():
    """Scan the MCP filesystem server"""

    print("=" * 70)
    print("MCP FUZZER - Standalone Security Scanner")
    print("=" * 70)
    print()

    # Create fuzzer instance
    fuzzer = MCPFuzzer(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        verbose=True,
        timeout=120
    )

    # Run focused scan on critical categories only
    print("[*] Running focused scan: command_injection, path_traversal, sql_injection")
    print()

    findings = await fuzzer.fuzz_server(
        categories=["command_injection", "path_traversal", "sql_injection"]
    )

    # Get summary
    summary = fuzzer.get_summary()

    # Print results
    print()
    print("=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)
    print()
    print(f"Total tests run: {summary['total_tests']}")
    print(f"Vulnerabilities found: {summary['total_findings']}")
    print()
    print("By Severity:")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count}")

    print()
    print("By Category:")
    for category, count in summary["by_category"].items():
        print(f"  {category}: {count}")

    # Show a few example findings
    if findings:
        print()
        print("=" * 70)
        print("SAMPLE FINDINGS (first 3)")
        print("=" * 70)
        print()

        for i, finding in enumerate(findings[:3], 1):
            print(f"[{i}] {finding.tool_name} - {finding.payload_category}")
            print(f"    Severity: {finding.severity}")
            print(f"    Parameter: {finding.parameter}")
            print(f"    Payload: {finding.payload[:80]}")
            print(f"    Reason: {finding.reason}")
            print()

    # Exit code based on severity
    if summary["by_severity"].get("CRITICAL", 0) > 0:
        print("⚠️  CRITICAL vulnerabilities found!")
        return 2
    elif summary["by_severity"].get("HIGH", 0) > 0:
        print("⚠️  HIGH severity vulnerabilities found!")
        return 1
    else:
        print("✓ No critical/high vulnerabilities found")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
