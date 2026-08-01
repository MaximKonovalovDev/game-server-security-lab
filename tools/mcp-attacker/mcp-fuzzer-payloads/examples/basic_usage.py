"""
Basic usage example for MCP Fuzzer

This example demonstrates how to use MCP Fuzzer programmatically
to test an MCP server for security vulnerabilities.
"""

import asyncio
from mcp_fuzzer import MCPFuzzer


async def main():
    """Run basic fuzzing example"""

    print("MCP Fuzzer - Basic Usage Example")
    print("=" * 50)

    # Create fuzzer instance for filesystem server
    # Replace with your MCP server command
    fuzzer = MCPFuzzer(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        verbose=True,  # Show detailed output
    )

    print("\n[*] Starting fuzzing...")
    print("[*] This will test the server with 150+ attack payloads")
    print("[*] Testing all vulnerability categories\n")

    # Run fuzzing (all categories)
    findings = await fuzzer.fuzz_server()

    # Get summary statistics
    summary = fuzzer.get_summary()

    # Print results
    print("\n" + "=" * 50)
    print("FUZZING COMPLETE")
    print("=" * 50)

    print(f"\nTotal tests run: {summary['total_tests']}")
    print(f"Vulnerabilities found: {summary['total_findings']}")
    print(f"Time elapsed: {summary['elapsed_seconds']:.2f}s")

    print("\nBy Severity:")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count}")

    if findings:
        print("\nDetailed Findings:")
        for i, finding in enumerate(findings, 1):
            print(f"\n[{i}] {finding.tool_name} - {finding.payload_category}")
            print(f"    Severity: {finding.severity}")
            print(f"    Parameter: {finding.parameter}")
            print(f"    Payload: {finding.payload[:50]}")
            if finding.cwe_id:
                print(f"    CWE: {finding.cwe_id}")
            if finding.remediation:
                print(f"    Remediation: {finding.remediation[:100]}...")
    else:
        print("\n✓ No vulnerabilities found!")


if __name__ == "__main__":
    asyncio.run(main())
