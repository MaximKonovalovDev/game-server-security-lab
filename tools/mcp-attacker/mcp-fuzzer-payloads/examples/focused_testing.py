"""
Focused testing example for MCP Fuzzer

This example shows how to test specific vulnerability categories
instead of running all tests.
"""

import asyncio
from mcp_fuzzer import MCPFuzzer


async def main():
    """Run focused fuzzing on high-risk categories"""

    print("MCP Fuzzer - Focused Testing Example")
    print("=" * 50)

    # Create fuzzer instance
    fuzzer = MCPFuzzer(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        verbose=False,  # Less verbose for focused testing
    )

    # Test only high-risk categories
    high_risk_categories = [
        "command_injection",  # CRITICAL
        "sql_injection",  # CRITICAL
        "ssrf",  # CRITICAL
        "path_traversal",  # HIGH
        "prompt_injection",  # HIGH
    ]

    print(f"\n[*] Testing {len(high_risk_categories)} high-risk categories:")
    for cat in high_risk_categories:
        print(f"    - {cat}")

    print("\n[*] Running focused fuzzing...\n")

    # Run fuzzing with specific categories
    findings = await fuzzer.fuzz_server(categories=high_risk_categories)

    # Get summary
    summary = fuzzer.get_summary()

    # Print results
    print("\n" + "=" * 50)
    print("FOCUSED FUZZING RESULTS")
    print("=" * 50)

    print(f"\nTests run: {summary['total_tests']}")
    print(f"Vulnerabilities: {summary['total_findings']}")
    print(f"Time: {summary['elapsed_seconds']:.2f}s")

    # Show critical/high findings only
    critical_high = [
        f for f in findings if f.severity in ["CRITICAL", "HIGH"]
    ]

    if critical_high:
        print(f"\n⚠️  Found {len(critical_high)} CRITICAL/HIGH severity issues:")
        for finding in critical_high:
            print(f"\n  {finding.severity}: {finding.tool_name}")
            print(f"  Category: {finding.payload_category}")
            print(f"  Parameter: {finding.parameter}")
            print(f"  CWE: {finding.cwe_id}")
            print(f"  Fix: {finding.remediation[:80]}...")
    else:
        print("\n✓ No CRITICAL or HIGH severity vulnerabilities found!")


if __name__ == "__main__":
    asyncio.run(main())
