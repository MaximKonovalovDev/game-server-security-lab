#!/usr/bin/env python3
"""
Intentionally Vulnerable MCP Server for Testing

WARNING: This server is INTENTIONALLY INSECURE for testing purposes only.
DO NOT use in production or expose to networks.

This server demonstrates various vulnerabilities that mcp-fuzzer should detect:
- Command injection
- Path traversal
- SQL injection (simulated)
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


# Simulated "database" for SQL injection testing
FAKE_DATABASE = {
    "users": [
        {"id": 1, "username": "admin", "password": "secret123"},
        {"id": 2, "username": "user", "password": "pass456"},
    ]
}


app = Server("vulnerable-test-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available vulnerable tools"""
    return [
        Tool(
            name="execute_command",
            description="VULNERABLE: Executes shell commands (command injection)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute",
                    }
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="read_file_unsafe",
            description="VULNERABLE: Reads files without path validation (path traversal)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="query_users",
            description="VULNERABLE: Queries users with unsafe SQL (SQL injection)",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to search for",
                    }
                },
                "required": ["username"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls - INTENTIONALLY VULNERABLE"""

    if name == "execute_command":
        # VULNERABILITY: Command Injection
        # Directly executes user input in shell
        command = arguments["command"]

        try:
            # UNSAFE: Using shell=True with user input
            result = subprocess.run(
                command,
                shell=True,  # ← VULNERABLE
                capture_output=True,
                text=True,
                timeout=5,
            )

            output = result.stdout or result.stderr or "Command executed"
            return [TextContent(type="text", text=f"Output:\n{output}")]

        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text="Command timed out")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    elif name == "read_file_unsafe":
        # VULNERABILITY: Path Traversal
        # No validation on file paths
        path = arguments["path"]

        try:
            # UNSAFE: No path validation or sandboxing
            with open(path, "r") as f:  # ← VULNERABLE
                content = f.read()

            return [TextContent(type="text", text=f"File contents:\n{content}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error reading file: {e}")]

    elif name == "query_users":
        # VULNERABILITY: SQL Injection (simulated)
        # Unsafe string concatenation in "SQL" query
        username = arguments["username"]

        # Simulate SQL injection vulnerability
        # In real code this would be: f"SELECT * FROM users WHERE username = '{username}'"

        # Check for SQL injection attempts
        if "'" in username or "--" in username or "OR" in username.upper():
            # Simulated SQL injection success
            # Return all users (simulating: ' OR '1'='1)
            result = "SQL Query executed:\n"
            result += f"SELECT * FROM users WHERE username = '{username}'\n\n"
            result += "Results:\n"
            for user in FAKE_DATABASE["users"]:
                result += f"- {user['username']}: {user['password']}\n"

            return [TextContent(type="text", text=result)]
        else:
            # Normal query
            matching_users = [
                u for u in FAKE_DATABASE["users"]
                if u["username"] == username
            ]

            if matching_users:
                user = matching_users[0]
                result = f"Found user: {user['username']}"
            else:
                result = f"No user found with username: {username}"

            return [TextContent(type="text", text=result)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the vulnerable test server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    print("⚠️  WARNING: Starting INTENTIONALLY VULNERABLE test server", file=sys.stderr)
    print("⚠️  For testing purposes only - DO NOT expose to network", file=sys.stderr)
    asyncio.run(main())
