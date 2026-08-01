#!/usr/bin/env python3
"""
Debug script to see what responses the vulnerable server returns
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path


async def main():
    """Test individual payloads against vulnerable server"""

    server_path = Path(__file__).parent / "tests" / "vulnerable_test_server.py"

    async with stdio_client(
        StdioServerParameters(
            command="python",
            args=[str(server_path)]
        )
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("=" * 70)
            print("TESTING COMMAND INJECTION")
            print("=" * 70)

            # Test command injection payloads
            cmd_payloads = ["whoami", "id", "ls -la"]

            for payload in cmd_payloads:
                print(f"\nPayload: {payload}")
                try:
                    result = await session.call_tool("execute_command", {"command": payload})
                    print(f"Response: {result.content}")
                except Exception as e:
                    print(f"Error: {e}")

            print("\n" + "=" * 70)
            print("TESTING SQL INJECTION")
            print("=" * 70)

            # Test SQL injection payloads
            sql_payloads = ["' OR '1'='1", "admin'--", "' OR 1=1--"]

            for payload in sql_payloads:
                print(f"\nPayload: {payload}")
                try:
                    result = await session.call_tool("query_users", {"username": payload})
                    print(f"Response: {result.content}")
                except Exception as e:
                    print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
