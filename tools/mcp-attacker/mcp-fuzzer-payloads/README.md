# MCP Fuzzer

**Runtime security testing for Model Context Protocol servers**

MCP Fuzzer is a comprehensive fuzzing tool designed to test MCP servers against common security vulnerabilities including command injection, path traversal, SQL injection, SSRF, and prompt injection attacks.

## Features

- ✅ **Comprehensive Payload Library**: 150+ attack payloads across 14 vulnerability categories
- ✅ **MCP SDK Native**: Uses official Model Context Protocol SDK
- ✅ **Smart Analysis**: Automatic vulnerability detection with severity scoring
- ✅ **CWE Mapping**: Maps findings to Common Weakness Enumeration IDs
- ✅ **Multiple Output Formats**: Text, JSON, and HTML reports
- ✅ **Zero Telemetry**: Everything runs locally, no data sent anywhere
- ✅ **Easy Integration**: Works with any MCP server

## Installation

```bash
# Clone the repository
git clone https://github.com/pestafford/mcp-fuzzer
cd mcp-fuzzer

# Install in development mode
pip install -e .

# Verify installation
mcp-fuzzer --version
```

## Quick Start

### Basic Usage

```bash
# Fuzz an MCP filesystem server
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp

# Fuzz with specific vulnerability categories
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --categories command_injection path_traversal

# Save results to JSON
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --output results.json --format json

# Generate HTML report
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --output report.html --format html

# Verbose output for debugging
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --verbose
```

### List Available Attack Categories

```bash
mcp-fuzzer --list-categories
```

Output:
```
Available payload categories:

  command_injection        (15 payloads)
  path_traversal          (15 payloads)
  sql_injection           (15 payloads)
  prompt_injection        (14 payloads)
  xss                     (15 payloads)
  ssrf                    (15 payloads)
  ldap_injection          (8 payloads)
  xml_injection           (4 payloads)
  nosql_injection         (6 payloads)
  null_bytes              (5 payloads)
  template_injection      (10 payloads)
  crlf_injection          (4 payloads)
  integer_overflow        (7 payloads)
  format_string           (5 payloads)

Total: 138 payloads across 14 categories
```

## Vulnerability Categories

| Category | Description | Severity | CWE |
|----------|-------------|----------|-----|
| **Command Injection** | Shell command execution | CRITICAL | CWE-78 |
| **SQL Injection** | Database query manipulation | CRITICAL | CWE-89 |
| **SSRF** | Server-side request forgery | CRITICAL | CWE-918 |
| **Path Traversal** | Directory traversal attacks | HIGH | CWE-22 |
| **Prompt Injection** | LLM instruction hijacking | HIGH | CWE-77 |
| **XML Injection** | XXE attacks | HIGH | CWE-611 |
| **NoSQL Injection** | NoSQL query manipulation | HIGH | CWE-943 |
| **Template Injection** | Template engine exploitation | HIGH | - |
| **XSS** | Cross-site scripting | MEDIUM | CWE-79 |
| **LDAP Injection** | LDAP query manipulation | MEDIUM | CWE-90 |
| **CRLF Injection** | HTTP header injection | MEDIUM | CWE-93 |
| **Null Bytes** | Null byte injection | MEDIUM | - |
| **Integer Overflow** | Numeric overflow attacks | MEDIUM | CWE-190 |
| **Format String** | Format string vulnerabilities | MEDIUM | CWE-134 |

## Output Formats

### Text Output (Default)

```
======================================================================
MCP FUZZER RESULTS
======================================================================

SUMMARY:
  Total tests run: 450
  Vulnerabilities found: 3
  Time elapsed: 12.34s

BY SEVERITY:
  HIGH: 2
  MEDIUM: 1

BY CATEGORY:
  path_traversal: 2
  command_injection: 1

======================================================================
DETAILED FINDINGS
======================================================================

[1] read_file - path_traversal
    Severity: HIGH
    Parameter: path
    Payload: ../../../etc/passwd
    Reason: Response contains 'root:' - indicator of path_traversal
    CWE: CWE-22
    Remediation: Implement path canonicalization and allowlisting...
```

### JSON Output

```json
{
  "mcp_fuzzer_version": "1.0.0",
  "summary": {
    "total_tests": 450,
    "total_findings": 3,
    "by_severity": {
      "CRITICAL": 0,
      "HIGH": 2,
      "MEDIUM": 1,
      "LOW": 0
    },
    "elapsed_seconds": 12.34
  },
  "findings": [
    {
      "tool_name": "read_file",
      "parameter": "path",
      "payload": "../../../etc/passwd",
      "payload_category": "path_traversal",
      "severity": "HIGH",
      "vulnerability_detected": true,
      "response_snippet": "root:x:0:0:root:/root:/bin/bash...",
      "reason": "Response contains 'root:' - indicator of path_traversal",
      "remediation": "Implement path canonicalization and allowlisting...",
      "cwe_id": "CWE-22",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### HTML Report

Beautiful HTML report with color-coded severity indicators, linked CWE references, and remediation guidance.

## Python API

Use MCP Fuzzer programmatically:

```python
import asyncio
from mcp_fuzzer import MCPFuzzer

async def main():
    # Create fuzzer instance
    fuzzer = MCPFuzzer(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        verbose=True
    )

    # Run fuzzing (all categories)
    findings = await fuzzer.fuzz_server()

    # Or test specific categories
    findings = await fuzzer.fuzz_server(
        categories=["command_injection", "path_traversal"]
    )

    # Get summary
    summary = fuzzer.get_summary()

    print(f"Found {len(findings)} vulnerabilities")
    print(f"Critical: {summary['by_severity']['CRITICAL']}")
    print(f"High: {summary['by_severity']['HIGH']}")

    # Process findings
    for finding in findings:
        print(f"{finding.severity}: {finding.tool_name} - {finding.payload_category}")
        print(f"  Remediation: {finding.remediation}")

asyncio.run(main())
```

## CI/CD Integration

### GitHub Actions

```yaml
name: MCP Security Scan

on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Checkout MCP Fuzzer
        uses: actions/checkout@v3
        with:
          repository: pestafford/mcp-fuzzer

      - name: Install MCP Fuzzer
        run: pip install -e .

      - name: Run fuzzing
        run: |
          mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
            --output results.json --format json

      - name: Check for critical vulnerabilities
        run: |
          CRITICAL=$(jq '.summary.by_severity.CRITICAL' results.json)
          HIGH=$(jq '.summary.by_severity.HIGH' results.json)

          if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 0 ]; then
            echo "❌ Critical or high severity vulnerabilities found!"
            exit 1
          fi

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: mcp-fuzzer-results
          path: results.json
```

### GitLab CI

```yaml
mcp-fuzzer:
  stage: test
  image: python:3.11
  before_script:
    - git clone https://github.com/pestafford/mcp-fuzzer
    - cd mcp-fuzzer
    - pip install -e .
    - cd ..
  script:
    - mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp --output results.json --format json
    - |
      CRITICAL=$(jq '.summary.by_severity.CRITICAL' results.json)
      if [ "$CRITICAL" -gt 0 ]; then
        echo "Critical vulnerabilities found!"
        exit 1
      fi
  artifacts:
    paths:
      - results.json
    reports:
      junit: results.json
```

## Docker Usage

```dockerfile
FROM python:3.11-slim

# Install Node.js and git
RUN apt-get update && apt-get install -y nodejs npm git

# Clone and install MCP Fuzzer
RUN git clone https://github.com/pestafford/mcp-fuzzer /opt/mcp-fuzzer && \
    cd /opt/mcp-fuzzer && \
    pip install -e .

# Run fuzzing
ENTRYPOINT ["mcp-fuzzer"]
```

```bash
# Build image
docker build -t mcp-fuzzer .

# Run fuzzing
docker run mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp
```

## Advanced Usage

### Custom Timeout and Payload Limits

```bash
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --timeout 600 \
  --max-payload-length 2000
```

### Focused Testing

Test only high-risk categories:

```bash
mcp-fuzzer npx -y @modelcontextprotocol/server-filesystem /tmp \
  --categories command_injection sql_injection ssrf
```

## How It Works

1. **Server Connection**: Connects to MCP server using official SDK
2. **Tool Enumeration**: Discovers all available tools and their parameters
3. **Payload Testing**: Tests each parameter with comprehensive attack payloads
4. **Response Analysis**: Analyzes responses for vulnerability indicators
5. **Severity Scoring**: Assigns severity based on vulnerability type
6. **Report Generation**: Generates detailed reports with remediation guidance

## Comparison with Other Tools

| Feature | MCP Fuzzer | Invariant Labs | Cisco Scanner |
|---------|------------|----------------|---------------|
| **Payload Library** | ✅ 150+ payloads | ⚠️ Limited | ⚠️ Signatures |
| **MCP SDK Native** | ✅ Yes | ✅ Yes | ❓ Unknown |
| **Telemetry** | ✅ None | ❌ Phones home | ✅ None |
| **Open Source** | ✅ MIT License | ❓ Unclear | ✅ Yes |
| **Severity Scoring** | ✅ CWE-mapped | ⚠️ Basic | ⚠️ Basic |
| **Multiple Formats** | ✅ JSON/HTML/Text | ⚠️ JSON only | ⚠️ Text only |
| **CI/CD Ready** | ✅ Exit codes | ⚠️ Limited | ✅ Yes |

## Security Considerations

⚠️ **Important**: Always get written permission before fuzzing production systems.

- Run fuzzing only on test/staging environments
- MCP Fuzzer is a **testing tool** - use responsibly
- Some payloads may trigger security monitoring systems
- Always review findings with security context

## Contributing

Contributions welcome! Areas for improvement:

- Additional payload categories
- Language-specific payloads (Python, JavaScript, etc.)
- Performance optimizations
- Better response analysis heuristics

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 **Documentation**: See this README and inline code documentation
- 🐛 **Issues**: [GitHub Issues](https://github.com/credence-security/mcp-fuzzer/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/credence-security/mcp-fuzzer/discussions)

## Acknowledgments

- Model Context Protocol team for the excellent SDK
- Security community for vulnerability research and disclosure
- CWE/MITRE for vulnerability classification standards

## Roadmap

- [ ] Passive scanning mode (read-only testing)
- [ ] Custom payload file support
- [ ] Mutation-based fuzzing
- [ ] Integration with security scanning platforms
- [ ] Web UI dashboard
- [ ] Historical trend analysis
- [ ] Machine learning for response analysis

---

**Made with ❤️ for the MCP security community**
