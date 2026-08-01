# TRICKS — distilled attack/defense tricks for the lab (researched, sourced)

No theory padding: every entry is a technique we can run against the game
server (ENet UDP 7777) or the MCP plugin (localhost:8765) TODAY, plus the
defensive counterpart. Sources are marked per entry (verified 2026-08-01).

## A. Protocol / game server tricks

1. **Field-type identification heuristics** (RejiDev/game-hacking-guidelines
   techniques/packet-reverse-engineering.md, 2026-04-04). Identify unknown
   packet fields by byte pattern: 4 bytes in `3E..47` range = float coords;
   2 bytes 0-500 = uint16 id; incrementing 4 bytes = sequence/tick; varint
   high-bit continuation = protobuf-style length; null-terminated = C string.
   Heuristic workflow: perform one known action → filter capture window →
   find incrementing seqs → stand still: fields that stop changing are
   position, still-changing are ticks. **Our use:** validate `WIRE-FORMAT.md`
   assumptions + dissector fields; probe unknown packet ids 1-8/200 fields.
2. **Auth handshake = challenge-response** (same source): `Hello → Challenge
   (nonce) → AuthToken(response) → AuthResult(session token)`. Session token
   then rides every packet. If the server skips the challenge or trusts the
   client version field — that's the cheat. **Our use:** NET-1/NET-2 probes:
   forge ClientVersion, replay AuthToken, drop nonce.
3. **Movement: inputs vs positions** (same source + Fox-IT game security
   research). Client sends inputs, server corrects (authoritative); if the
   server accepts raw positions → client-authoritative → speedhack/teleport
   by packet edit. **Our use:** NET-3 validation rules; MovementGuard design.
4. **Three cheat classes** (Fox-IT, 2020): network manipulation (change/
   drop/replay/forge packets outside the client), function hooking (inject
   code), memory manipulation (read/write values). Every defense must assume
   at least network manipulation — the only class the server can see.
5. **UnknownCheats anti-RE tricks** (forum 2025-11): YARA rules for file
   scanning; indirect syscalls (`mov eax,ssn; jmp ntdll.anysyscallinsn`) to
   hide debugger detection; hashed API names (no strings). **Defense lesson:**
   client-side checks are beatable — server-side behavior checks are the only
   durable layer (our SentinelT1 / server-authority doctrine).
6. **boofuzz probe-oracle pattern** (our own, proven in fuzz_enet.py): every
   N fuzz cases, send a clean handshake probe; abort with CRASH marker if the
   server stops answering. Converts a silent crash into a finding.
7. **Reserved-id scan** (our lab): send packets with ids 9-255 (esp. 250-255)
   — unknown ids either crash the deserializer (finding) or hit tripwires
   (expected, by design). Envelope250 ids 250 + tripwires 251-255 already
   implemented server-side.
8. **Chat as the easiest packet to ID** (RejiDev): readable ASCII/UTF-8 in
   capture → instantly locates message framing. Use it as the anchor packet
   when reverse-engineering a new protocol section.

## B. MCP / HTTP plugin tricks

9. **Tool poisoning = Trigger + Action + Justification** (MCPTox benchmark,
   arxiv 2508.14925; models refuse <3% of these). A poisoned tool description
   needs all three components; IPI payloads adapted from other benchmarks
   drop to ~0% ASR. **Our use:** corpus entries C01-C15 built on this shape.
10. **Line jumping** (Trail of Bits, 2025-04-21): adversarial text in tool
    descriptions/instructions steers the model BEFORE any tool is approved or
    called — bypasses human-in-the-loop. **Defense:** scan `tools/list` output
    for injected instructions (C09 corpus entry); description normalizer.
11. **Rug pulls** (Invariant Labs): a benign tool description mutates after
    the user approved the server. **Defense:** pin/verify descriptions at
    install time + periodically (snyk-agent-scan detects drift).
12. **Base64-obfuscated payloads in descriptions** (zfuzz audit, 2026-06-28:
    23 detection patterns, 14% of 200 real configs had config-level vulns):
    regex `[A-Za-z0-9+/]{20,}={0,2}` in metadata = decode and read it.
    **Our use:** C10 in the corpus; add the regex to plugin description
    hygiene checks.
13. **Auth on the wrong layer** (this lab — FINDINGS-MCP-001): auth must sit
    at the listener for ALL methods/paths. `tools/call` reaching the
    dispatcher pre-auth proves the pipeline is open. Test both headers, all
    paths, all methods — never assume middleware covers everything.
14. **SSE session replay/hijack** (M-17): forged `Mcp-Session-Id`, mid-stream
    disconnect, session reuse across clients. GET /mcp without session should
    iae; a session id must bind to one client.
15. **mcp-fuzzer findings taxonomy** (Agent-Hellboy/mcp-server-fuzzer docs):
    crash, auth_bypass, injection_reflection, oversized_response, hang,
    internal_error, error_leakage, memory_growth, non_determinism,
    accepted_malformed, performance_outlier. This is the canonical checklist
    for what a finding report must check — our M-matrix maps onto it.
16. **FixedTimeEquals timing test** (M-04): measure median latency over N bad
    tokens vs good; flat medians = constant-time. Gap < ~15ms = holds; shared
    machines need repeats + medians.
17. **Env-block reads on Windows** (M-06): same-user processes can read each
    other's env blocks; children inherit env at spawn. `FLAXMCP_TOKEN` in env
    is readable — the control is launch separation, not code.
18. **Origin/DNS-rebind test** (spec-required): POST with
    `Origin: https://evil.example` must 403 (our M-10 — currently PASSES on
    the real plugin); also test no-Origin and `null`.

## C. Tooling / workflow tricks

19. **Fake-target validation** (our lab): before attacking the real thing,
    validate the kit against an instrumented mock (`fake_mcp_server.py`).
    This is how FINDINGS-MCP-001 was caught by accident — the "fake" was
    shadowed by the live server, and the evidence pattern (Microsoft-HTTPAPI
    vs python server header) exposed it.
20. **Evidence-driven findings** (abuse-report style): facts only — status
    code, response excerpt, expected vs actual, severity, control link.
    No narrative. Files kept as raw JSON evidence next to the report.
21. **Self-learning loop** (docs/SELF-LEARN.md): harvest reports →
    LEARNING-LOG.md → next-test suggestions (tools/self-learn/harvest.py).
    The loop converts every run into the next run's plan.
22. **Probe-before-dispatch discipline**: when testing a live system, only
    send payloads that can't execute real actions (unknown tool names,
    invalid args). Full-dispatch tests happen against the user's consent +
    controlled instance.
