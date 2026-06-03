# PRD — Exercise 02: Debate Between Two AI Agents Under a Judge

**Document type:** Product Requirements Document (PRD)
**Status:** Draft v1.0
**Course:** AI Agents — HW2
**Submission:** Pair, GitHub (public / shared with lecturer)

---

## 1. Overview

### 1.1 Problem statement
Build a multi-agent system in which **two debating agents** argue opposite sides of an
open topic, supervised and judged by a **third agent (the Father / Judge)**. The judge
moderates the debate, routes every message, prevents the debaters from collapsing into
mutual agreement, and at the end **declares a winner** — a tie is forbidden.

The exercise is fundamentally about **Context Engineering and agent orchestration**:
`Command → Skill → Agent → Subagent`. The quality differentiator is a clean class
hierarchy, conscious management of the context window, and disciplined orchestration —
not merely a working chat loop.

### 1.2 Core metaphor
The debate is judged like the TV game **"Truth is a Lie"**: the criterion is
**persuasiveness, not factual correctness**. Lying is permitted; the opposing agent is
expected to catch it. This is part of the persuasion skill being measured.

### 1.3 Goals
- Three LLM-backed agents in a strict hierarchy (Judge orchestrates two debaters).
- A real, LLM-generated debate (never Python-faked text).
- At least **10** argument↔counterargument exchanges per side (5 allowed under budget,
  must be disclosed in the README).
- A decisive, explained verdict with differential scoring (e.g., 80% / 70%).
- Production-grade engineering: OOP, config-driven, tested, linted, observable, secure.

### 1.4 Non-goals
- Determining objective truth about the topic.
- A polished consumer GUI (optional; terminal menu is the required interface).
- Real-time human participation in the argument itself (humans only configure & observe).

---

## 2. Architecture

### 2.1 Agent hierarchy and message routing

```
                       ┌──────────────────────────┐
                       │     Father / Judge        │
                       │  - moderator / host       │
                       │  - topic-BLIND            │
                       │  - relays every message   │
                       │  - enforces the rules     │
                       │  - declares the winner    │
                       └───────────┬──────────────┘
                       relays      │      relays
                ┌──────────────────┴──────────────────┐
        ┌───────▼────────┐                    ┌────────▼───────┐
        │   Pro Agent     │                    │   Con Agent     │
        │  - skill A      │                    │  - skill B      │
        │  - PRO position │                    │  - CON position │
        └────────────────┘                    └────────────────┘

   MANDATORY message flow:   Child → Father → Child
   (debaters NEVER talk to each other directly)
```

### 2.2 Layered software architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Interface Layer        Terminal Menu  │  (optional GUI)      │
├─────────────────────────────────────────────────────────────┤
│  SDK Layer (public API) DebateSDK — usable WITHOUT the menu   │
│                         lets the tester / agent drive it      │
│                         programmatically (self-debugging)     │
├─────────────────────────────────────────────────────────────┤
│  Orchestration Layer    DebateEngine (routes Child→Father→…)  │
│                         Watchdog + keep-alive + restart       │
├─────────────────────────────────────────────────────────────┤
│  Agent Layer            BaseAgent ─┬─ JudgeAgent              │
│                                    ├─ DebaterAgent ─┬─ ProAgent│
│                                    │                └─ ConAgent│
├─────────────────────────────────────────────────────────────┤
│  Services Layer         LLMProvider │ WebSearchTool │          │
│                         Gatekeeper  │ FifoLogger    │ Config   │
├─────────────────────────────────────────────────────────────┤
│  Cross-cutting          JSON message protocol, timeouts,      │
│                         structured logging, error handling    │
└─────────────────────────────────────────────────────────────┘
```

The **SDK layer is independent of the interface**. Whether the front-end is a terminal
menu, a CLI flag, a UI, or an API, the same SDK is called underneath. This separation is
what allows the AI agent to debug itself by driving the SDK directly.

### 2.3 Class diagram (logical)

```
                       ┌───────────────┐
                       │  «abstract»    │
                       │   BaseAgent    │
                       ├───────────────┤
                       │ - agent_id     │
                       │ - role         │
                       │ - llm: LLMProvider
                       │ - logger       │
                       │ - config       │
                       ├───────────────┤
                       │ + send(msg)→Msg│  (timeout-wrapped LLM call)
                       │ + build_prompt()│ (abstract)
                       │ + system_prompt()│(abstract)
                       └──────┬─────────┘
              ┌───────────────┼─────────────────────┐
              │               │                     │
      ┌───────▼──────┐ ┌──────▼────────┐    (shared debater logic)
      │  JudgeAgent   │ │ «abstract»    │
      ├──────────────┤ │ DebaterAgent  │
      │ + moderate()  │ ├───────────────┤
      │ + relay()     │ │ - position    │
      │ + intervene() │ │ - skill       │
      │ + verdict()   │ │ - web: WebSearchTool
      │   (no tie)    │ ├───────────────┤
      └──────────────┘ │ + argue()      │
                       │ + rebut(opp)   │
                       │ + research(q)  │
                       └──────┬─────────┘
                       ┌──────┴───────┐
                ┌──────▼─────┐  ┌─────▼──────┐
                │  ProAgent   │  │  ConAgent   │
                │ skill A     │  │ skill B     │
                └─────────────┘  └─────────────┘

  Services (composition, not inheritance):
  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────┐ ┌──────────┐
  │ LLMProvider   │ │ WebSearchTool │ │ Gatekeeper │ │ FifoLogger │ │ Config   │
  │ «abstract»    │ ├──────────────┤ ├────────────┤ ├───────────┤ ├──────────┤
  │ +complete()   │ │ +search(q)    │ │ +check()   │ │ +log()    │ │ +get()   │
  └──────┬───────┘ └──────────────┘ │ +record()  │ │ (FIFO     │ └──────────┘
   ┌─────┴─────┐                     │ +blocked() │ │  rotation)│
   │Anthropic  │                     └────────────┘ └───────────┘
   │OpenAI     │
   │MockLLM(test)│
   └───────────┘

  Orchestration:
  ┌────────────────┐        ┌───────────────┐
  │  DebateEngine   │ uses → │   Watchdog     │ (keep-alive, kill & restart)
  │  + run_debate() │        └───────────────┘
  └───────┬────────┘
          │ exposed via
  ┌───────▼────────┐        ┌───────────────┐
  │   DebateSDK     │ ←────  │ TerminalMenu   │
  └────────────────┘        └───────────────┘
```

### 2.4 No code duplication
All behavior common to every agent (LLM call wrapping, timeout, retry, logging, JSON
envelope construction, gatekeeper checks) lives in **`BaseAgent`**. Logic common to both
debaters (argue / rebut / research, persona injection) lives in **`DebaterAgent`**.
`ProAgent` and `ConAgent` differ only by their **position** and **distinct skill**.

---

## 3. Functional requirements

### 3.1 The debate loop
- **FR-1** The system runs a debate on a configurable open topic (e.g., Barcelona vs.
  Real Madrid, freshwater vs. saltwater fish, best diet).
- **FR-2** Every message follows **Child → Father → Child**. Debaters have no direct
  channel; the Judge relays.
- **FR-3** At least **N_ROUNDS** exchanges per side (default 10; configurable down to 5,
  with README disclosure when reduced).
- **FR-4** **Mutual response:** each debater turn must explicitly rebut the opponent's
  *most recent* argument (passed in by the Judge), not argue in parallel.
- **FR-5** Each debater has a **distinct skill/persona** ensuring genuine opposition.

### 3.2 The Judge / Father
- **FR-6** The Judge is **topic-blind**: it receives the transcript and the rhetoric
  rules, but is not told which side is "objectively right." (Reduces bias.)
- **FR-7** The Judge **relays** each debater message to the opponent.
- **FR-8** **Anti-agreement enforcement:** if a debater capitulates / agrees with the
  opponent across the board, the Judge **intervenes and reminds the agent of its role**.
  Per-point concessions are allowed; wholesale agreement is not.
- **FR-9** **Verdict with no tie:** at the end the Judge declares a single winner with a
  **differential score** (e.g., 80% / 70%) and a written rationale. Equal scores are
  impossible by construction.
- **FR-10** The verdict criterion is **persuasiveness**, not factual accuracy.

### 3.3 Tools
- **FR-11** A real **internet search tool** is wired into the debaters and is mandatory.
  Debaters may call it to fetch references supporting their arguments.

### 3.4 Communication format
- **FR-12** All inter-agent messages use a **JSON envelope** — structured, templated,
  monitorable, testable, token-efficient. (Schema in §6.)

### 3.5 Interfaces
- **FR-13** A **terminal menu** (keyboard-driven) lets a tester configure and run a
  debate, view the transcript, and read the verdict.
- **FR-14** The same capabilities are available **directly via the SDK** (no menu),
  so the tester can drive it programmatically.
- **FR-15** (Optional) GUI — if built, screenshots must be attached.

---

## 4. Non-functional requirements

### 4.1 Reliability & resilience
- **NFR-1 Timeouts:** every LLM / tool request is wrapped with a configurable timeout.
- **NFR-2 Watchdog + keep-alive:** an autonomous watchdog monitors agent liveness; if a
  process/agent hangs or crashes, it is **killed and restarted**.
- **NFR-3 Retries:** transient failures are retried with backoff (configurable).

### 4.2 Security / cyber
- **NFR-4** No API keys in Git. `.env` is in `.gitignore`. Only **`.env.example`** is
  committed.
- **NFR-5 Gatekeeper:** a financial/usage blocking layer enforces spend & call limits
  and halts the run before exceeding them.

### 4.3 Observability
- **NFR-6 Structured logs** via a FIFO-rotation logger configured in the config file
  (e.g., **20 files, ≤500 lines each**; oldest deleted first).
- **NFR-7** The full session transcript is persisted (JSON + human-readable) for the
  README "full dialogue log of session 1."

### 4.4 Code quality
- **NFR-8 OOP** with a well-designed class hierarchy and inheritance; **no code
  duplication**; shared logic in shared classes.
- **NFR-9 TDD + unit tests** (pytest), with a deterministic **MockLLM** so tests need no
  network / no API key / no spend.
- **NFR-10 Ruff** lint + format must pass clean.
- **NFR-11 No hardcoded parameters** — everything in a config file.

### 4.5 Environment & packaging
- **NFR-12 UV** virtual environment; **`pyproject.toml`** fully provisions the tester's
  environment.
- **NFR-13** Python 3.11+.

### 4.6 Content policy
- **NFR-14** Respectful discourse: no shouting, no cursing; politically correct. Per-turn
  word/time limits enforced via config.
- **NFR-15** Output language English or Hebrew (not Arabic), per the lecturer's request.

---

## 5. Configuration (no hardcoded params)

A single config file (`config.yaml` or `config.toml`) plus `.env` for secrets. Indicative
keys:

```
llm:
  provider: anthropic            # anthropic | openai | mock
  judge_model:    claude-...     # judge may use a different model
  debater_model:  claude-...
  temperature:    0.8            # debaters more creative
  judge_temperature: 0.2         # judge more deterministic
  max_tokens:     800
debate:
  topic: "Which is better: Barcelona or Real Madrid?"
  rounds_per_side: 10            # may set to 5 (disclose in README)
  max_words_per_turn: 150
  pro_skill: "evidence-and-data persuader"
  con_skill: "emotional-and-rhetorical persuader"
timeouts:
  request_seconds: 60
  retries: 2
  backoff_seconds: 2
watchdog:
  keepalive_seconds: 15
  max_restarts: 3
gatekeeper:
  max_total_calls: 80
  max_total_usd: 2.00
  max_tokens_total: 200000
search:
  provider: ...                  # web search backend
  max_results: 3
logging:
  dir: ./logs
  fifo_max_files: 20
  fifo_max_lines_per_file: 500
  level: INFO
```

Secrets (`.env`, never committed): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`SEARCH_API_KEY`, etc. `.env.example` documents the names with placeholder values.

---

## 6. JSON message protocol

Every inter-agent message is a JSON envelope. Indicative schema:

```json
{
  "schema_version": "1.0",
  "message_id": "uuid",
  "timestamp": "ISO-8601",
  "from": "pro | con | judge",
  "to": "pro | con | judge",
  "type": "argument | rebuttal | relay | intervention | verdict | system",
  "round": 3,
  "payload": {
    "text": "the argument / rebuttal text",
    "rebuts_message_id": "uuid-of-opponent-msg",   // mutual-response link
    "citations": [{"title": "...", "url": "...", "snippet": "..."}],
    "word_count": 142
  },
  "meta": {
    "tokens_used": 512,
    "latency_ms": 1840,
    "model": "claude-..."
  }
}
```

Verdict message payload (judge only):

```json
{
  "winner": "pro | con",          // never null, never "tie"
  "scores": { "pro": 80, "con": 70 },   // strict inequality enforced
  "rationale": "why this side was MORE PERSUASIVE (not more correct)",
  "highlights": { "pro": ["..."], "con": ["..."] }
}
```

**Tie-prevention is enforced in code**, not just in the prompt: if the model returns equal
scores, the engine applies a deterministic tie-break and/or re-queries the judge for a
decisive ranking, guaranteeing a strict winner.

---

## 7. Acceptance criteria (Definition of Done)

1. Running `uv run python -m debate` opens a **terminal menu**; a debate can be run,
   watched, and its verdict read entirely from the keyboard.
2. The **same debate** can be launched **directly via the SDK** in a few lines of Python.
3. A completed run shows **≥10 exchanges per side** (or 5, disclosed), each rebuttal
   linked to the opponent's prior message (mutual response verifiable in JSON).
4. The Judge produces a **decisive verdict** with differential scores and a rationale;
   no tie is ever produced.
5. The Judge **intervenes** at least when a debater over-agrees (demonstrable via a forced
   test scenario / MockLLM).
6. A **web search tool** is invoked during the debate and citations appear in the log.
7. All inter-agent traffic is **JSON** and persisted; logs use **FIFO rotation**.
8. **Timeouts + watchdog** demonstrably recover from a hung/crashed agent.
9. **Gatekeeper** halts the run when a configured limit is reached (demonstrable).
10. `ruff check` and `ruff format --check` pass; `pytest` passes with **MockLLM**
    (no network).
11. `.env` is git-ignored; only `.env.example` is committed; no keys in history.
12. **README.md** contains: architecture diagram, prompts, screenshots, and the **full
    dialogue log of session 1**; **`pyproject.toml`** provisions the environment via UV.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| LLMs drift to agreement (people-pleasing) | Distinct skills + judge anti-agreement intervention + adversarial system prompts |
| Judge leaks/uses topic knowledge → bias | Topic-blind judge prompt; pass only transcript + rhetoric rules |
| Model returns a tie | Code-level strict-inequality enforcement + tie-break re-query |
| Runaway spend | Gatekeeper hard limits on calls/tokens/USD |
| Hung agent | Per-request timeout + watchdog kill-and-restart |
| Leaked API key | `.env` git-ignored, `.env.example` only, pre-commit check |
| Flaky/networked tests | MockLLM + recorded fixtures for deterministic TDD |

---

## 9. Deliverables checklist

- [ ] Source code (OOP, layered, no duplication)
- [ ] `config.*` + `.env.example` (`.env` git-ignored)
- [ ] `pyproject.toml` (UV-provisionable)
- [ ] Terminal menu + SDK entry points
- [ ] Web search tool integration
- [ ] Watchdog, timeouts, gatekeeper, FIFO logger
- [ ] Unit tests (pytest) + MockLLM; Ruff clean
- [ ] Architecture/class diagram (in README + this PRD)
- [ ] README.md: screenshots, prompts, full session-1 dialogue log
- [ ] Public / shared GitHub repo
- [ ] Pair submission (same repo link, PDF per partner in Moodle)
