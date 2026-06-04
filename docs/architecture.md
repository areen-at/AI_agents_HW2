# Architecture

This document expands the layer and class diagrams from `prd.md §2` and maps
them onto the real source tree. Every `.py` file is ≤ 150 lines, so each box
below corresponds to one small, single-responsibility module.

---

## 1. Layered software architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Interface Layer        ui/menu.py + ui/actions.py            │
│                         (keyboard terminal menu)              │
├─────────────────────────────────────────────────────────────┤
│  SDK Layer (public API) sdk.py — DebateSDK                    │
│                         interface-agnostic; tester/agent      │
│                         drives this directly (self-debugging) │
├─────────────────────────────────────────────────────────────┤
│  Orchestration Layer    orchestration/engine.py  (Engine)     │
│                         router.py · round.py · transcript.py  │
│                         watchdog.py (keep-alive, kill/restart)│
├─────────────────────────────────────────────────────────────┤
│  Agent Layer            agents/base.py    (BaseAgent)         │
│                           ├─ agents/judge.py    (JudgeAgent)  │
│                           └─ agents/debater.py  (DebaterAgent)│
│                                ├─ agents/pro.py       (Pro)   │
│                                └─ agents/con_agent.py (Con)   │
├─────────────────────────────────────────────────────────────┤
│  Services Layer         llm/* (provider + resilience)         │
│                         tools/web_search.py · gatekeeper/*    │
│                         observability/* · config/* · prompts/*│
├─────────────────────────────────────────────────────────────┤
│  Cross-cutting          protocol/* (JSON message + verdict),  │
│                         security/* (sanitizer/egress/moderate)│
└─────────────────────────────────────────────────────────────┘
```

The **SDK is independent of the interface**. The terminal menu, a human tester,
and the agent itself all call the same `DebateSDK`, so behaviour is identical
regardless of front-end (`sdk.py`).

---

## 2. Agent hierarchy and message routing

```
                       ┌──────────────────────────┐
                       │     Father / Judge        │
                       │  - topic-BLIND moderator  │
                       │  - relays every message   │
                       │  - intervenes on agreement│
                       │  - declares the winner    │
                       └───────────┬──────────────┘
                       relays      │      relays
                ┌──────────────────┴──────────────────┐
        ┌───────▼────────┐                    ┌────────▼───────┐
        │   Pro Agent     │                    │   Con Agent     │
        │  evidence/data  │                    │  emotion/rhetoric│
        │  PRO position   │                    │  CON position   │
        └────────────────┘                    └────────────────┘

   MANDATORY flow:  Child → Father → Child
   (debaters NEVER address each other directly — enforced in router.py)
```

`orchestration/router.py` raises `RoutingError` if any message is not addressed
*to* the judge, so a direct Pro↔Con path cannot exist even by mistake.

---

## 3. Class diagram (logical)

```
                       «abstract» BaseAgent            (agents/base.py)
                       - agent_id, role
                       - llm: LLMProvider
                       - logger, config
                       + send(...) -> Message          (resilient, gatekept, redacted)
                       + system_prompt()  (abstract)
                       + build_prompt()   (abstract)
                              │
              ┌───────────────┴─────────────────┐
        JudgeAgent                       «abstract» DebaterAgent
        (agents/judge.py)                (agents/debater.py)
        + relay(msg)                     - position, skill
        + should_intervene(text)         - web: WebSearchTool | None
        + intervene(to, reason)          + argue(round, context, citations)
        + verdict(text) -> Verdict       + rebut(opponent_msg, round, citations)
          (strict-inequality, no tie)    + research(query) -> [Citation]
                                                │
                                   ┌────────────┴───────────┐
                              ProAgent                   ConAgent
                              (agents/pro.py)            (agents/con_agent.py)
                              skill A                    skill B
                              (differ only by position + skill)

  Services (composition, not inheritance):
    LLMProvider «abstract» (llm/base.py) ── Anthropic | OpenAI | Groq | MockLLM
        wrapped by llm/resilience.py (timeout + retry/backoff + circuit breaker)
    WebSearchTool (tools/web_search.py)  — egress-guarded, sanitised, cached
    Gatekeeper    (gatekeeper/limiter.py)— check()/record()/blocked()
    FifoLogger    (observability/fifo_logger.py) — redacted, FIFO-rotated JSONL
    Config        (config/schema.py)     — typed, validated, no magic numbers

  Orchestration:
    Engine (orchestration/engine.py) ── uses ── Watchdog (kill & restart)
        exposed via DebateSDK (sdk.py) ◄── TerminalMenu (ui/)
```

**Note on naming:** the Con debater lives in `agents/con_agent.py`, not
`con.py` — `con` is a reserved device name on Windows and would break native
git on that platform. Likewise the Con prompt is `prompts/con_side.md`.

---

## 4. One debate, end to end

1. `DebateSDK.run_debate()` builds a `FifoLogger`, a `Gatekeeper`, an optional
   `WebSearchTool`, and an `Engine` (`bootstrap.py` assembles the services).
2. `Engine.from_config()` builds the Judge and both debaters; every provider is
   wrapped by `llm/resilience.py`, so **no agent ever calls a vendor SDK
   directly** — that wrapper is the single choke-point for timeout, retry,
   circuit-breaking, gatekeeper accounting, and redacted logging.
3. For each of `rounds_per_side` rounds, `Round.play()` runs Pro then Con:
   - the debater does **one** cached web-research call (stable per-side query),
   - produces a turn addressed to the judge,
   - `Router` has the judge relay it to the opponent (and intervene if the turn
     is conceding/over-agreeing),
   - the relay is fed to the opponent as its next incoming message, linked via
     `rebuts_message_id` — guaranteeing **mutual response**.
   - every turn is wrapped by `Watchdog.run`, so a hang is timed out and the
     turn is killed and restarted (bounded by `max_restarts`).
4. After the last round, `JudgeAgent.verdict()` scores the transcript on
   **persuasiveness only** and returns a `Verdict` whose model forbids a tie;
   a code-level tie-break guarantees a strict winner even if the model returns
   equal scores.
5. `DebateResult(transcript, verdict)` is returned; the menu renders it.

---

## 5. Module → responsibility map

| Package | Responsibility |
|---|---|
| `config/` | Load + validate YAML, resolve secrets from env (never echoed) |
| `protocol/` | JSON `Message` envelope, `Verdict` (no-tie invariant), builders |
| `observability/` | Redaction + FIFO-rotated structured logging |
| `security/` | Sanitizer (injection), egress (anti-SSRF/TLS), moderation |
| `gatekeeper/` | USD/token/call budget accounting + hard limits |
| `llm/` | Provider abstraction + resilience wrapper + deterministic mock |
| `tools/` | Hardened web search + citation parsing |
| `prompts/` | Pro/Con/Judge system prompts as loadable assets |
| `agents/` | BaseAgent → JudgeAgent / DebaterAgent → Pro / Con |
| `orchestration/` | Router, Round, Transcript, Engine, Watchdog |
| `sdk.py` | Interface-agnostic public API |
| `ui/` | Terminal menu + action handlers (no business logic) |
