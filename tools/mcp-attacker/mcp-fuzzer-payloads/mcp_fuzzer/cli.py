"""
Command-line interface for MCP Fuzzer
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from .fuzzer import MCPFuzzer
from .payloads import PayloadLibrary


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""

    parser = argparse.ArgumentParser(
        description="MCP Fuzzer - Runtime security testing for Model Context Protocol servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fuzz MCP filesystem server
  mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp

  # Fuzz with specific categories only
  mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \\
    --categories command_injection path_traversal

  # Save results to JSON
  mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \\
    --output results.json

  # Verbose output with all details
  mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \\
    --verbose

Available payload categories:
  - command_injection    - Command execution attacks
  - path_traversal      - Directory traversal attacks
  - sql_injection       - SQL injection attacks
  - prompt_injection    - LLM prompt injection
  - xss                 - Cross-site scripting
  - ssrf                - Server-side request forgery
  - ldap_injection      - LDAP injection
  - xml_injection       - XML external entity attacks
  - nosql_injection     - NoSQL injection
  - template_injection  - Template injection
  - crlf_injection      - HTTP header injection
  - null_bytes          - Null byte injection
  - integer_overflow    - Integer overflow
  - format_string       - Format string attacks
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",  # Make optional
        help="Command to start MCP server (e.g., npx, python, node)"
    )

    parser.add_argument(
        "args",
        nargs="*",
        help="Arguments for the MCP server command",
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="Specific payload categories to test (default: all)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Overall fuzzing timeout in seconds (default: 300)",
    )

    parser.add_argument(
        "--max-payload-length",
        type=int,
        default=1000,
        help="Maximum payload length to test (default: 1000)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Save results to JSON file",
    )

    parser.add_argument(
        "--format",
        choices=["json", "text", "html"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all available payload categories and exit",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.1",
    )

    return parser


def format_text_output(findings, summary):
    """Format findings as human-readable text"""

    output = []
    output.append("=" * 70)
    output.append("MCP FUZZER RESULTS")
    output.append("=" * 70)
    output.append("")

    # Summary
    output.append("SUMMARY:")
    output.append(f"  Total tests run: {summary['total_tests']}")
    output.append(f"  Vulnerabilities found: {summary['total_findings']}")

    if summary["elapsed_seconds"]:
        output.append(f"  Time elapsed: {summary['elapsed_seconds']:.2f}s")

    output.append("")

    # Severity breakdown
    output.append("BY SEVERITY:")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            output.append(f"  {severity}: {count}")

    output.append("")

    # Category breakdown
    if summary["by_category"]:
        output.append("BY CATEGORY:")
        for category, count in sorted(
            summary["by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            output.append(f"  {category}: {count}")
        output.append("")

    # Tool breakdown
    if summary["by_tool"]:
        output.append("BY TOOL:")
        for tool, count in sorted(
            summary["by_tool"].items(), key=lambda x: x[1], reverse=True
        ):
            output.append(f"  {tool}: {count}")
        output.append("")

    # Detailed findings
    if findings:
        output.append("=" * 70)
        output.append("DETAILED FINDINGS")
        output.append("=" * 70)
        output.append("")

        for i, finding in enumerate(findings, 1):
            output.append(f"[{i}] {finding.tool_name} - {finding.payload_category}")
            output.append(f"    Severity: {finding.severity}")
            output.append(f"    Parameter: {finding.parameter}")
            output.append(f"    Payload: {finding.payload[:100]}")

            if finding.reason:
                output.append(f"    Reason: {finding.reason}")

            if finding.cwe_id:
                output.append(f"    CWE: {finding.cwe_id}")

            if finding.error:
                output.append(f"    Error: {finding.error[:200]}")
            elif finding.response_snippet:
                output.append(f"    Response: {finding.response_snippet[:200]}")

            if finding.remediation:
                output.append(f"    Remediation: {finding.remediation}")

            output.append("")

    else:
        output.append("✓ No vulnerabilities found!")
        output.append("")

    return "\n".join(output)


def format_json_output(findings, summary):
    """Format findings as JSON"""

    findings_data = []
    for finding in findings:
        findings_data.append(
            {
                "tool_name": finding.tool_name,
                "parameter": finding.parameter,
                "payload": finding.payload,
                "payload_category": finding.payload_category,
                "severity": finding.severity,
                "vulnerability_detected": finding.vulnerability_detected,
                "response_snippet": finding.response_snippet,
                "error": finding.error,
                "reason": finding.reason,
                "remediation": finding.remediation,
                "cwe_id": finding.cwe_id,
                "timestamp": finding.timestamp,
            }
        )

    result = {
        "mcp_fuzzer_version": "1.0.0",
        "summary": summary,
        "findings": findings_data,
    }

    return json.dumps(result, indent=2)


def format_html_output(findings, summary):
    """Format findings as HTML report"""

    # Simple HTML template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>MCP Fuzzer Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .finding {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .critical {{ border-left: 4px solid #d9534f; }}
        .high {{ border-left: 4px solid #f0ad4e; }}
        .medium {{ border-left: 4px solid #5bc0de; }}
        .low {{ border-left: 4px solid #5cb85c; }}
        .severity {{ font-weight: bold; padding: 2px 8px; border-radius: 3px; }}
        .critical-badge {{ background: #d9534f; color: white; }}
        .high-badge {{ background: #f0ad4e; color: white; }}
        .medium-badge {{ background: #5bc0de; color: white; }}
        .low-badge {{ background: #5cb85c; color: white; }}
        code {{ background: #f8f8f8; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>MCP Fuzzer Results</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total tests:</strong> {summary['total_tests']}</p>
        <p><strong>Vulnerabilities found:</strong> {summary['total_findings']}</p>
        <p><strong>Time elapsed:</strong> {summary['elapsed_seconds']:.2f}s</p>

        <h3>By Severity</h3>
        <ul>
"""

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = summary["by_severity"].get(severity, 0)
        if count > 0:
            html += f"            <li>{severity}: {count}</li>\n"

    html += """        </ul>
    </div>

    <h2>Detailed Findings</h2>
"""

    if findings:
        for i, finding in enumerate(findings, 1):
            severity_class = finding.severity.lower()
            html += f"""
    <div class="finding {severity_class}">
        <h3>Finding #{i}: {finding.tool_name}</h3>
        <p><span class="severity {severity_class}-badge">{finding.severity}</span></p>
        <p><strong>Category:</strong> {finding.payload_category}</p>
        <p><strong>Parameter:</strong> <code>{finding.parameter}</code></p>
        <p><strong>Payload:</strong> <code>{finding.payload[:100]}</code></p>
"""

            if finding.reason:
                html += f"        <p><strong>Reason:</strong> {finding.reason}</p>\n"

            if finding.cwe_id:
                html += f"        <p><strong>CWE:</strong> <a href='https://cwe.mitre.org/data/definitions/{finding.cwe_id[4:]}.html' target='_blank'>{finding.cwe_id}</a></p>\n"

            if finding.remediation:
                html += (
                    f"        <p><strong>Remediation:</strong> {finding.remediation}</p>\n"
                )

            html += "    </div>\n"
    else:
        html += "    <p>✓ No vulnerabilities found!</p>\n"

    html += """
</body>
</html>
"""

    return html


async def main():
    """Main CLI entry point"""

    parser = create_parser()
    args = parser.parse_args()

    # List categories if requested
    if args.list_categories:
        all_payloads = PayloadLibrary.get_all_payloads()
        print("Available payload categories:\n")
        for category, payloads in all_payloads.items():
            print(f"  {category:25s} ({len(payloads)} payloads)")
        print(f"\nTotal: {PayloadLibrary.get_total_count()} payloads across {len(all_payloads)} categories")
        sys.exit(0)

    # Validate that command is provided
    if not args.command:
        parser.error("the following arguments are required: command")

    # Validate categories if specified
    if args.categories:
        all_categories = set(PayloadLibrary.get_all_payloads().keys())
        invalid_categories = set(args.categories) - all_categories
        if invalid_categories:
            print(f"Error: Invalid categories: {', '.join(invalid_categories)}")
            print(f"Use --list-categories to see available options")
            sys.exit(1)

    # Create fuzzer
    fuzzer = MCPFuzzer(
        server_command=args.command,
        server_args=args.args,
        timeout=args.timeout,
        max_payload_length=args.max_payload_length,
        verbose=args.verbose,
    )

    # Run fuzzing
    try:
        findings = await fuzzer.fuzz_server(categories=args.categories)
        summary = fuzzer.get_summary()

        # Format output
        if args.format == "json":
            output = format_json_output(findings, summary)
        elif args.format == "html":
            output = format_html_output(findings, summary)
        else:  # text
            output = format_text_output(findings, summary)

        # Write to file or stdout
        if args.output:
            args.output.write_text(output)
            print(f"Results saved to: {args.output}")
        else:
            print(output)

        # Exit code based on findings
        if summary["by_severity"].get("CRITICAL", 0) > 0:
            sys.exit(2)  # Critical vulnerabilities found
        elif summary["by_severity"].get("HIGH", 0) > 0:
            sys.exit(1)  # High vulnerabilities found
        else:
            sys.exit(0)  # No critical/high vulnerabilities

    except KeyboardInterrupt:
        print("\n\n[!] Fuzzing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def cli_main():
    """Entry point for console script"""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
