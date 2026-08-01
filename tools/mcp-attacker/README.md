# tools/mcp-attacker — attacker kit for the FlaxMCP plugin (lab use only)

Attacks run against the **local** editor MCP endpoint (`http://localhost:8765/mcp`)
per `docs/MCP-ATTACK-LAB.md` doctrine. Never point this at a tunneled/public
endpoint. Everything emits facts; the orchestrator builds findings reports.

## Layout

```
mcp_attack.py          stdlib-only raw HTTP/SSE attacker client (13 modes, M-01..M-38)
fuzz_mcp.py            boofuzz HTTP fuzzer for POST /mcp (transport group M-12..M-16)
injection-corpus.json  Position-C payloads (tool poisoning, policy override, ...)
mcp-server-fuzzer/     vendored Agent-Hellboy/mcp-server-fuzzer (MIT) - CLI: mcp-fuzzer
mcp-poisoning-poc/     vendored gensecaihq/mcp-poisoning-poc (MIT) - attack demos + sanitizer
mcpwn/                 vendored Teycir/Mcpwn (MIT) - automated MCP scanner
.venv/                 venv with `mcp-fuzzer` CLI installed (pip install mcp-fuzzer)
```

## Quick start

```powershell
# control case (needs token):
.\.venv\Scripts\python.exe mcp_attack.py --mode baseline --token $env:FLAXMCP_TOKEN

# auth group, no token needed:
.\.venv\Scripts\python.exe mcp_attack.py --mode no-token --count 5
.\.venv\Scripts\python.exe mcp_attack.py --mode wrong-token --count 20
.\.venv\Scripts\python.exe mcp_attack.py --mode timing --token $env:FLAXMCP_TOKEN --count 80

# transport group:
.\.venv\Scripts\python.exe mcp_attack.py --mode origin-spoof
.\.venv\Scripts\python.exe mcp_attack.py --mode method-fuzz
.\.venv\Scripts\python.exe mcp_attack.py --mode batch --token $env:FLAXMCP_TOKEN
.\.venv\Scripts\python.exe mcp_attack.py --mode flood --token $env:FLAXMCP_TOKEN --concurrency 64
.\.venv\Scripts\python.exe mcp_attack.py --mode sse --token $env:FLAXMCP_TOKEN
.\.venv\Scripts\python.exe mcp_attack.py --mode openapi
.\.venv\Scripts\python.exe mcp_attack.py --mode endpoints

# tool dispatch group (editor + project loaded):
.\.venv\Scripts\python.exe mcp_attack.py --mode arg-bombs --token $env:FLAXMCP_TOKEN

# Position B:
.\.venv\Scripts\python.exe mcp_attack.py --mode env-probe

# boofuzz transport fuzz (tool ID M-12..M-16):
..\boofuzz\.venv\Scripts\python.exe fuzz_mcp.py --host 127.0.0.1 --port 8765 --cases 800
```

## Vendored tools (real code, runnable)

| Kit | What it is | How to run (lab) |
|---|---|---|
| `mcp-fuzzer` (PyPI pkg of mcp-server-fuzzer) | tool-arg + protocol-type fuzzing, findings.json in canonical taxonomy | `.venv\Scripts\mcp-fuzzer.exe --mode all --phase both --protocol http --endpoint http://localhost:8765/mcp --enable-safety-system` |
| `mcp-poisoning-poc/` | attack demo servers + MCPSanitizer (MIT) | `python examples/basic_attack_demo.py` |
| `mcpwn/` | automated scanner: auth_bypass, prompt_injection, resource_exhaustion, ssrf... (MIT) | spawns servers via command (stdio) — point at any server we build: `python mcpwn.py --safe-mode <cmd>` |
| `mcp-attack-labs/` | hands-on attack labs: tool poisoning, shadowing, DockerDash, RAG, agentic memory, A2A kill chain | per-lab code, e.g. `python labs/01-mcp-tool-poisoning/attack1_direct_poison.py` |
| `mcp-fuzzer-payloads/` | 138 attack payloads / 14 vuln categories + debug vulnerable server (installed as pkg) | `python debug_vulnerable_server.py` + `mcp-fuzzer` |
| `fuzzd/` | Rust adversarial MCP tester: chained/stateful attacks + TPA corpora (rug_pull, tool_poisoning, tool_shadowing) | `cargo build --release` (done) → `target\release\fuzzd ...` |
| `pentest-ai/` | offensive MCP server, 205 wrapped tools (MIT) | BYO LLM; `pip install -r requirements.txt` then run its server |
| `mcp-injection-experiments/` | tool-poisoning PoC snippets (NO LICENSE — study only, don't ship) | read the snippets; also mirrored under mcp-attack-labs/01/reference |
| garak (pip) | NVIDIA LLM vuln scanner (real code, installed 0.15.1) | `.venv\Scripts\garak.exe --model_type ... ` (probe our LLM wiring) |
| rebuff (pip) | prompt-injection detector (installed) | `python -c "from rebuff import Rebuff; ..."` — test detection rate on corpus |
| scapy (pip) | packet crafting/sniffing (installed 2.7.0) | craft arbitrary game packets for netcode probes |

## Rebuilding

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install mcp-fuzzer rebuff scapy garak
.\.venv\Scripts\pip.exe install -e .\mcp-fuzzer-payloads
cd fuzzd && cargo build --release
```
