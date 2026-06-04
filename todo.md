# TODO — Exercise 02: Debate Between Two AI Agents

**Derived from:** `prd.md` + `plan.md`
**Convention:** `[ ]` open · `[x]` done · `[~]` in progress · `[!]` blocked
**Global rule:** every `.py` file ≤ **150 lines**. Every phase ends **green**
(`ruff` + `bandit` + `pytest` + file-length check).

> Legend of gates used below:
> - **G-LINT** = `ruff check` + `ruff format --check` clean
> - **G-SEC** = `bandit` + `gitleaks` + `pip-audit` clean
> - **G-TEST** = `pytest` all green
> - **G-LEN** = no tracked `.py` over 150 lines
> - **G-ALL** = all of the above

---

## Phase 0 — Bootstrap & safety rails

### 0.1 Repository & version control
- [ ] Confirm working dir is a git repo; create working branch off `main`
- [ ] Decide branch name (e.g., `feat/debate-system`)
- [ ] Add top-level `README.md` placeholder (filled in Phase 9)
- [ ] Keep `prd.md`, `plan.md`, `todo.md` tracked at repo root

### 0.2 `.gitignore` (BEFORE first commit — cyber requirement)
- [ ] Create `.gitignore`
- [ ] Ignore `.env`
- [ ] Ignore `.venv/`
- [ ] Ignore `logs/`
- [ ] Ignore `__pycache__/`, `*.pyc`
- [ ] Ignore `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- [ ] Ignore `dist/`, `build/`, `*.egg-info/`
- [ ] Ignore IDE files (`.idea/`, `.vscode/`)
- [ ] Verify `git status` never shows `.env`

### 0.3 Secrets templates
- [ ] Create `.env.example` with secret **names** only (no real values):
  - [ ] `ANTHROPIC_API_KEY=`
  - [ ] `OPENAI_API_KEY=`
  - [ ] `SEARCH_API_KEY=`
- [ ] Add a header comment: "copy to `.env`, fill values, NEVER commit `.env`"
- [ ] Confirm `.env` is NOT created/committed in this phase

### 0.4 `pyproject.toml` (UV-provisionable)
- [ ] Create `pyproject.toml` with `[project]` metadata (name, version, py>=3.11)
- [ ] Add runtime deps: `anthropic`, `openai` (optional extra), `pydantic`, `pyyaml`,
      `httpx`
- [ ] Add dev deps group: `pytest`, `pytest-cov`, `ruff`, `bandit`, `pip-audit`,
      `pre-commit`
- [ ] Configure `[tool.ruff]` (line-length, target-version, selected rule sets)
- [ ] Configure `[tool.ruff.format]`
- [ ] Configure `[tool.pytest.ini_options]` (testpaths, addopts)
- [ ] Configure `[tool.bandit]` (paths, skips if justified)
- [ ] Configure `[tool.coverage]` thresholds for core/security paths
- [ ] Run `uv sync` and confirm lockfile `uv.lock` is generated
- [ ] Commit `uv.lock` (pinned, hash-verified)

### 0.5 Line-length enforcement tooling
- [ ] Create `scripts/check_file_length.py` (fails if any tracked `.py` > 150 lines)
  - [ ] Reads max from config/constant (no hardcode in two places)
  - [ ] Walks `src/` and `tests/` `.py` files
  - [ ] Prints offending file + line count
  - [ ] Exit code 1 on violation
- [ ] Create `tests/test_file_length.py` asserting the cap across the repo

### 0.6 Pre-commit hooks
- [ ] Create `.pre-commit-config.yaml`
  - [ ] `ruff` (lint) hook
  - [ ] `ruff-format` hook
  - [ ] `bandit` hook
  - [ ] `gitleaks` hook (block secrets)
  - [ ] local hook → `scripts/check_file_length.py`
- [ ] `pre-commit install`
- [ ] Run `pre-commit run --all-files` and confirm clean

### 0.7 Config skeleton
- [ ] Create `config.yaml` with the full key set from PRD §5:
  - [ ] `llm.*` (provider, judge_model, debater_model, temperatures, max_tokens)
  - [ ] `debate.*` (topic, rounds_per_side, max_words_per_turn, pro_skill, con_skill)
  - [ ] `timeouts.*` (request_seconds, retries, backoff_seconds)
  - [ ] `watchdog.*` (keepalive_seconds, max_restarts)
  - [ ] `gatekeeper.*` (max_total_calls, max_total_usd, max_tokens_total)
  - [ ] `search.*` (provider, max_results, **egress allowlist**)
  - [ ] `logging.*` (dir, fifo_max_files, fifo_max_lines_per_file, level)
  - [ ] `security.*` (moderation toggles, sanitizer limits)

### 0.8 Package skeleton
- [ ] Create `src/debate/__init__.py`
- [ ] Create empty package dirs with `__init__.py`: `config/`, `protocol/`,
      `observability/`, `security/`, `gatekeeper/`, `llm/`, `tools/`, `prompts/`,
      `agents/`, `orchestration/`, `ui/`
- [ ] Create thin `src/debate/__main__.py` printing a banner
- [ ] Run `uv run python -m debate` → banner shows

### 0.9 Phase 0 exit gate
- [ ] **G-LINT** clean
- [ ] **G-SEC** clean (bandit/gitleaks on skeleton)
- [ ] **G-LEN** clean
- [ ] **G-TEST** (file-length test green)
- [ ] `git status` shows no `.env`
- [ ] Commit: "phase 0: bootstrap, safety rails, length enforcement"

---

## Phase 1 — Cross-cutting services

### 1.1 Config loader (`config/`)
- [x] `config/schema.py`: typed pydantic models for each config section
  - [x] Validate ranges (e.g., rounds ≥ 1, usd > 0, files > 0)
  - [x] Reject unknown/missing required keys
- [x] `config/secrets.py`: resolve secrets from env
  - [x] `get_secret(name)` returns value or raises clear error (no value in message)
  - [x] Helper to mask a secret for safe display (`sk-...abcd`)
- [x] `config/loader.py`: load `config.yaml`, merge env, return typed config object
  - [x] Fail-fast on missing required secret
  - [x] Single public `load_config(path)` entry
- [x] **Tests** `tests/test_config.py`:
  - [x] loads a valid sample config
  - [x] rejects missing required key
  - [x] rejects out-of-range value
  - [x] missing secret raises WITHOUT leaking expected value

### 1.2 JSON protocol (`protocol/`)
- [x] `protocol/message.py`: `Message` envelope model (PRD §6)
  - [x] fields: schema_version, message_id, timestamp, from, to, type, round, payload, meta
  - [x] enum for `from`/`to` (pro|con|judge) and `type`
  - [x] payload validation (text, rebuts_message_id, citations, word_count)
- [x] `protocol/verdict.py`: `Verdict` model with **no-tie invariant**
  - [x] `winner` ∈ {pro, con}; never null, never "tie"
  - [x] `scores.pro != scores.con` enforced (validator raises on equality)
  - [x] rationale + highlights fields
- [x] `protocol/builder.py`: helpers to construct envelopes (id/timestamp generation)
- [x] **Tests** `tests/test_protocol_message.py`:
  - [x] round-trip serialize/deserialize
  - [x] invalid message rejected
- [x] **Tests** `tests/test_verdict_no_tie.py`:
  - [x] equal scores rejected at model level
  - [x] null/"tie" winner rejected
  - [x] valid differential verdict accepted

### 1.3 Observability (`observability/`)
- [x] `observability/redaction.py`:
  - [x] regex/known-key scrubbing of secrets/PII
  - [x] `redact(text) -> text` used by ALL log writes
  - [x] redact common key patterns (sk-, Bearer, api_key=…)
- [x] `observability/fifo_logger.py`:
  - [x] writes structured (JSON line) entries
  - [x] rotation: ≤ `fifo_max_lines_per_file` per file
  - [x] rotation: ≤ `fifo_max_files`; delete oldest first (FIFO)
  - [x] applies `redact()` before writing
  - [x] config-driven dir/level/limits
- [x] **Tests** `tests/test_redaction.py`:
  - [x] planted secret is masked in output
- [x] **Tests** `tests/test_fifo_logger.py`:
  - [x] exceeding line cap rolls a new file
  - [x] exceeding file cap deletes oldest
  - [x] secret never written verbatim

### 1.4 Gatekeeper (`gatekeeper/`)
- [x] `gatekeeper/budget.py`: accounting of calls, tokens, USD
  - [x] cost estimation per provider/model (from config rates)
  - [x] running totals
- [x] `gatekeeper/limiter.py`:
  - [x] `check(estimated)` raises/blocks if a limit would be crossed
  - [x] `record(actual)` updates totals after a call
  - [x] `blocked()` / status accessor
- [x] **Tests** `tests/test_gatekeeper.py`:
  - [x] allows under all limits
  - [x] blocks at call limit
  - [x] blocks at token limit
  - [x] blocks at USD limit

### 1.5 Phase 1 exit gate
- [x] **G-ALL** clean
- [x] Commit: "phase 1: config, protocol, logging, redaction, gatekeeper"

---

## Phase 2 — Security primitives

### 2.1 Sanitizer (`security/sanitizer.py`) — prompt-injection containment
- [x] Wrap untrusted text as **quoted data, never instructions**
- [x] Strip/escape known injection markers ("ignore previous instructions", system-y text)
- [x] Enforce max length cap (config)
- [x] Add an explicit "the following is untrusted external content" framing helper
- [x] **Tests** `tests/test_sanitizer_injection.py`:
  - [x] "ignore previous instructions…" payload is neutralized/quoted
  - [x] overly long content is truncated
  - [x] benign content passes through intact

### 2.2 Egress control (`security/egress.py`) — anti-SSRF
- [x] Domain **allowlist** from config
- [x] Enforce HTTPS / TLS verification
- [x] Block private/loopback/link-local IP ranges
- [x] Reject redirects to disallowed hosts
- [x] `validate_url(url) -> bool/raise`
- [x] **Tests** `tests/test_egress_allowlist.py`:
  - [x] off-allowlist domain rejected
  - [x] loopback/private IP rejected
  - [x] allowlisted https URL accepted

### 2.3 Moderation (`security/moderation.py`)
- [x] Detect offensive language / cursing (configurable list/policy)
- [x] Enforce respectful-tone policy
- [x] Enforce per-turn **word cap** (from config)
- [x] `check_text(text) -> (ok, reason)`
- [x] **Tests** `tests/test_moderation.py`:
  - [x] cursing flagged
  - [x] over-word-limit flagged
  - [x] clean respectful text passes

### 2.4 Phase 2 exit gate
- [x] **G-ALL** clean
- [x] Commit: "phase 2: security primitives (sanitizer, egress, moderation)"

---

## Phase 3 — LLM provider layer

### 3.1 Provider contract (`llm/base.py`)
- [x] Define `Completion` dataclass/model (text, tokens_used, model, latency_ms)
- [x] Abstract `LLMProvider.complete(system, messages, **opts) -> Completion`
- [x] Define provider-selection factory (reads `llm.provider` from config) — `llm/factory.py`

### 3.2 Resilience wrapper (`llm/resilience.py`)
- [x] **Timeout** per request (config `request_seconds`)
- [x] **Retry + backoff** on transient errors (config `retries`, `backoff_seconds`)
- [x] **Circuit breaker** (open after N consecutive failures) — `llm/circuit.py`
- [x] Gatekeeper `check()` before call, `record()` after
- [x] Redacted logging of request/response metadata
- [x] Single decorator/wrapper reused by ALL providers (no duplication)
- [x] **Tests** `tests/test_llm_resilience.py`:
  - [x] timeout path handled
  - [x] retry on transient error then success
  - [x] circuit breaker trips after threshold
  - [x] gatekeeper invoked (check + record)

### 3.3 Mock provider (`llm/mock.py`)
- [x] Deterministic, scriptable responses (queue/sequence)
- [x] Canned "over-agreement" output (for judge-intervention test)
- [x] Canned "tie / equal-score" output (for no-tie test)
- [x] No network, no key, no spend

### 3.4 Real providers
- [x] `llm/anthropic.py` (default): map contract → Anthropic SDK
- [x] `llm/openai.py` (optional): map contract → OpenAI SDK
- [x] Both go through `resilience.py` (never called raw)

### 3.5 Phase 3 exit gate
- [x] **G-ALL** clean (real providers smoke-tested manually, skipped in CI)
- [x] Commit: "phase 3: LLM abstraction + resilience + mock"

---

## Phase 4 — Web search tool (mandatory)

### 4.1 Citation model (`tools/citations.py`)
- [x] `Citation` model: title, url, snippet
- [x] Parser from raw provider response → `list[Citation]`

### 4.2 Web search tool (`tools/web_search.py`)
- [x] `search(query) -> list[Citation]`
- [x] Route outbound through `security/egress.py`
- [x] Pass all results through `security/sanitizer.py`
- [x] Timeout + gatekeeper-aware
- [x] Graceful degradation: on failure return `[]` + log (debate continues)
- [x] Config: provider + `max_results`

### 4.3 Tests `tests/test_web_search.py`
- [x] mocked HTTP → parsed citations
- [x] failure path → `[]` + logged
- [x] all returned snippets are sanitized
- [x] off-allowlist host blocked before request

### 4.4 Live smoke test (manual, documented)
- [ ] One real query against the chosen provider
- [ ] Capture output for README evidence

### 4.5 Phase 4 exit gate
- [x] **G-ALL** clean
- [x] Commit: "phase 4: hardened web search tool"

---

## Phase 5 — Agent hierarchy (OOP core)

### 5.1 Prompts as assets (`prompts/`)
- [x] `prompts/loader.py`: load a template by name (+ `render_prompt` for skill injection)
- [x] `prompts/pro.md`: Pro persona + **distinct skill A** (e.g., data/evidence persuader)
- [x] `prompts/con.md`: Con persona + **distinct skill B** (e.g., emotional/rhetorical)
- [x] `prompts/judge.md`: **topic-blind** judge; rules of rhetoric; persuasion-not-truth;
      no-tie mandate; anti-agreement duty
- [x] Ensure Pro/Con prompts explicitly resist people-pleasing / never fully concede

### 5.2 BaseAgent (`agents/base.py`)
- [x] Abstract base: holds `llm`, `logger`, `config`, `agent_id`, `role`
- [x] `send()` builds JSON envelope → calls LLM (resilient/gatekept) → logs (redacted) →
      returns `Message`
- [x] Abstract `system_prompt()` and `build_prompt()`
- [x] All shared agent logic lives here (no duplication downstream)
- [x] **Tests** `tests/test_agents_base.py`:
  - [x] produces a valid JSON envelope (MockLLM)
  - [x] logs are redacted

### 5.3 DebaterAgent (`agents/debater.py`)
- [x] Abstract: adds `position`, `skill`, `web` tool
- [x] `argue(context)` — opening / positional argument
- [x] `rebut(opponent_msg)` — references opponent's last message id
- [x] `research(query)` — calls web search, attaches citations
- [x] Enforces **word cap** + **moderation** before returning
- [x] Injects persona/skill into system prompt (real opposition)
- [x] **Tests** `tests/test_debater.py`:
  - [x] enforces word cap
  - [x] rebuttal links opponent `rebuts_message_id`
  - [x] research attaches sanitized citations

### 5.4 Pro & Con (`agents/pro.py`, `agents/con_agent.py` — `con` is a Windows reserved name)
- [x] `ProAgent`: position=PRO, skill A; differs ONLY by position + skill
- [x] `ConAgent`: position=CON, skill B; differs ONLY by position + skill
- [x] Verify no duplicated logic vs. `DebaterAgent`

### 5.5 JudgeAgent (`agents/judge.py`)
- [x] **Topic-blind** system prompt (transcript + rhetoric rules only)
- [x] `relay(msg)` — pass a debater message toward the opponent
- [x] `intervene(reason)` — anti-agreement reminder of role
- [x] `verdict(transcript) -> Verdict`:
  - [x] strict-inequality scoring (no tie)
  - [x] code-level tie-break / re-query if model returns equal
  - [x] rationale grounded in **persuasiveness**, not truth
- [x] **Tests** `tests/test_judge_intervention.py`:
  - [x] fires on canned "I totally agree with you" message
- [x] **Tests** (verdict no-tie already in Phase 1 model test) — add agent-level:
  - [x] forced equal-score MockLLM → tie-break yields a strict winner

### 5.6 Phase 5 exit gate
- [x] **G-ALL** clean
- [x] Manual review: zero duplicated logic across agents
- [x] Commit: "phase 5: agent hierarchy (base/debater/pro/con/judge) + prompts"

---

## Phase 6 — Orchestration

### 6.1 Router (`orchestration/router.py`)
- [x] Enforce **Child → Father → Child**: every debater message goes through judge
- [x] No direct Pro↔Con path exists in the API
- [x] Judge may inspect/relay/intervene before forwarding

### 6.2 Round execution (`orchestration/round.py`)
- [x] Execute one exchange (argument → relay → counterargument)
- [x] Guarantee **mutual response**: feed opponent's last relayed message
- [x] Link `rebuts_message_id` on each rebuttal
- [x] Trigger judge intervention when over-agreement detected

### 6.3 Transcript (`orchestration/transcript.py`)
- [x] Accumulate all messages (ordered)
- [x] Persist full JSON transcript via FIFO logger
- [x] Provide human-readable export

### 6.4 Engine (`orchestration/engine.py`)
- [x] Thin coordinator: build Judge + Pro + Con from config
- [x] Loop `rounds_per_side` exchanges (default 10; 5 allowed/disclosed)
- [x] End with `judge.verdict()` → decisive winner
- [x] Wire watchdog around each turn

### 6.5 Watchdog (`orchestration/watchdog.py`)
- [x] Keep-alive per agent turn
- [x] On timeout/crash → **kill & restart** the agent (bounded `max_restarts`)
- [x] Log every restart
- [x] Surface unrecoverable failure cleanly

### 6.6 Tests
- [x] `tests/test_engine_routing.py`:
  - [x] no direct Pro↔Con traffic (all via judge)
  - [x] rebuttals link the correct prior message
  - [x] exactly `rounds_per_side` exchanges per side
  - [x] verdict is decisive (no tie)
- [x] `tests/test_watchdog.py`:
  - [x] hung MockLLM turn is timed out, killed, restarted
  - [x] run recovers and completes

### 6.7 Phase 6 exit gate
- [x] **G-ALL** clean
- [x] Full debate runs end-to-end on MockLLM
- [x] Commit: "phase 6: orchestration (router/round/transcript/engine/watchdog)"

---

## Phase 7 — SDK & interface layers

### 7.1 SDK (`sdk.py`)
- [x] `DebateSDK.run_debate(topic=None, rounds=None) -> DebateResult`
- [x] Accessors: `.transcript`, `.verdict`
- [x] Interface-agnostic (no print/menu logic here)
- [x] Usable in ~5 lines of Python (self-debug entry point)
- [x] **Tests** `tests/test_sdk.py`:
  - [x] full MockLLM debate → decisive verdict + correct exchange count

### 7.2 Terminal menu (`ui/menu.py`, `ui/actions.py`)
- [x] `ui/menu.py`: render keyboard menu loop
  - [x] `[1] Configure topic/rounds`
  - [x] `[2] Run debate (live print)`
  - [x] `[3] View last transcript`
  - [x] `[4] View verdict`
  - [x] `[5] Settings`
  - [x] `[0] Exit`
- [x] `ui/actions.py`: action handlers → call `DebateSDK` only (no business logic)
- [x] Input validation on menu selections
- [x] **Tests**: menu smoke-tested with scripted stdin

### 7.3 Entry point
- [x] `__main__.py` launches the menu
- [x] `uv run python -m debate` → working menu

### 7.4 Phase 7 exit gate
- [x] **G-ALL** clean
- [x] Both run paths verified (menu + SDK)
- [x] Commit: "phase 7: SDK + terminal menu interface"

---

## Phase 8 — Hardening, real run, audit

### 8.1 Real wiring
- [x] Configure real LLM provider + key in `.env` (local only)
- [~] Configure real web-search provider + egress allowlist (configured; no SEARCH_API_KEY present)
- [x] Choose session-1 topic (e.g., Barcelona vs. Real Madrid)

### 8.2 Real debate run (session 1)
- [x] Run a full debate (10 rounds/side, or 5 with disclosure)
- [x] Save full **JSON transcript**
- [x] Save **human-readable transcript**
- [x] Save the **verdict** (winner + differential scores + rationale)

### 8.3 Evidence capture (for README)
- [!] Screenshot: terminal menu  (manual capture pending)
- [!] Screenshot: debate running (live)  (manual capture pending)
- [!] Screenshot: verdict screen  (manual capture pending)
- [ ] (Optional GUI) screenshots if a GUI is built

### 8.4 Engineering-feature demonstrations
- [x] Demonstrate **gatekeeper block** (lower a limit, show halt) + capture
- [x] Demonstrate **watchdog restart** (inject a hang) + capture
- [x] Demonstrate **timeout handling** + capture
- [x] Demonstrate **prompt-injection containment** (planted payload neutralized) + capture
- [x] Demonstrate **judge intervention** on over-agreement + capture

### 8.5 Security audit
- [x] `bandit` clean (or all findings triaged/justified)
- [x] `pip-audit` clean (or CVEs accepted with rationale)
- [~] `gitleaks` clean (binary not installed locally; pinned in pre-commit + manual history scan clean)
- [x] Scan FULL git history → confirm `.env`/keys never committed
- [x] Confirm only `.env.example` is tracked

### 8.6 Coverage & quality
- [x] Raise coverage on core + security paths to target
- [x] `ruff` + `ruff format` final pass
- [x] **G-LEN** final pass across whole repo

### 8.7 Phase 8 exit gate
- [~] **G-ALL** clean + demos captured (screenshots + live web search pending)
- [x] Commit: "phase 8: real session, demos, security audit"

---

## Phase 9 — Documentation & submission

### 9.1 Architecture docs (`docs/`)
- [x] `docs/architecture.md`: layer diagram + **class diagram** (from PRD §2.3)
- [x] `docs/threat-model.md`: expanded STRIDE table + controls

### 9.2 README.md (the graded artifact)
- [x] Project overview
- [x] **Rules of the game**: persuasion-not-truth, no tie, topic-blind judge,
      lying allowed, anti-agreement
- [x] **Architecture + class diagram** (embed/reference `docs/`)
- [x] **Threat model summary** + security controls
- [x] Setup via **UV**: `uv sync`, run menu, run via SDK (copy-paste commands)
- [x] **Prompts** used: Pro, Con, Judge (full text)
- [~] **Screenshots** (menu, running debate, verdict) — text evidence committed;
      image capture pending manual run
- [x] **Full dialogue log of session 1** (readable)
- [x] Engineering notes: timeouts, watchdog, gatekeeper, FIFO logging, JSON protocol,
      security controls
- [x] **Budget disclosure** if rounds reduced 10 → 5
- [x] Language note (English/Hebrew, not Arabic)
- [x] How to run tests + linters (`pytest`, `ruff`, `bandit`)

### 9.3 Repository hygiene
- [x] Confirm `.env.example` committed; `.env` absent
- [~] `pyproject.toml` provisions the env (`uv sync` / pip -e); `uv.lock` not yet
      committed (generated on first `uv sync` — uv not installed in dev env)
- [ ] Make repo **public** (or share with lecturer) — verify access  (manual)
- [ ] Tag/release the submission commit  (manual)

### 9.4 Submission (pair)
- [ ] Same repo link for both partners
- [ ] Each partner creates the PDF containing the repo link
- [ ] Each partner submits the PDF separately in Moodle
- [ ] Double-check lecturer access (rejection = no resubmit)

### 9.5 Final gate
- [ ] **G-ALL** clean on the submission commit
- [ ] README renders correctly on GitHub
- [ ] All acceptance criteria (PRD §7) satisfied

---

## Acceptance criteria checklist (mirrors PRD §7)

- [ ] AC-1 `uv run python -m debate` opens a keyboard-driven terminal menu; debate runs,
      watchable, verdict readable from the menu
- [ ] AC-2 The same debate launches directly via the SDK in a few lines
- [ ] AC-3 A run shows ≥10 exchanges/side (or 5 disclosed); each rebuttal links the
      opponent's prior message (mutual response verifiable in JSON)
- [ ] AC-4 Judge produces a decisive verdict (differential scores + rationale); no tie ever
- [ ] AC-5 Judge intervenes on over-agreement (demonstrable via forced scenario)
- [~] AC-6 Web search tool wired into the loop (round.py research per side, cached) +
      citations attach to turns — mock/stub-tested; live run pending a Tavily key
- [ ] AC-7 All inter-agent traffic is JSON and persisted; logs use FIFO rotation
- [ ] AC-8 Timeouts + watchdog recover from a hung/crashed agent
- [ ] AC-9 Gatekeeper halts the run at a configured limit
- [ ] AC-10 `ruff` clean; `pytest` green with MockLLM (no network)
- [ ] AC-11 `.env` git-ignored; only `.env.example` committed; no keys in history
- [ ] AC-12 README has diagram, prompts, screenshots, full session-1 log;
      `pyproject.toml` provisions env via UV

---

## Security checklist (mirrors PRD §4.2 + threat model)

- [ ] SEC-1 No API keys in git (history scanned)
- [ ] SEC-2 `.env` in `.gitignore`; `.env.example` only
- [ ] SEC-3 Secrets redacted from all logs
- [ ] SEC-4 Prompt-injection containment on all web/tool content
- [ ] SEC-5 Egress allowlist + TLS verification + anti-SSRF
- [ ] SEC-6 Gatekeeper hard limits (USD/tokens/calls) enforced
- [ ] SEC-7 Per-request timeout + circuit breaker
- [ ] SEC-8 Content moderation (no offensive language) + word caps
- [ ] SEC-9 Dependency scan (`pip-audit`) + SAST (`bandit`) clean
- [ ] SEC-10 Verdict tie-smuggling impossible (model + code invariant)

---

## Cross-cutting quality gates (apply to EVERY commit)

- [ ] Q-1 Every `.py` ≤ 150 lines (G-LEN)
- [ ] Q-2 `ruff check` + `ruff format --check` clean (G-LINT)
- [ ] Q-3 `bandit` + `gitleaks` clean (G-SEC)
- [ ] Q-4 `pytest` green (G-TEST)
- [ ] Q-5 No code duplication (shared logic in base classes)
- [ ] Q-6 No hardcoded params (everything via config)
- [ ] Q-7 Each new module has a matching test
- [ ] Q-8 Commit message names the phase/sub-component

---

## Open decisions to resolve (gating Phase 3)

- [x] D-1 LLM backend: Anthropic (default) / OpenAI / both behind abstraction
- [x] D-2 Session-1 topic: Barcelona vs. Real Madrid
- [~] D-3 Web-search provider: Tavily (api.tavily.com allowlist); research() now wired
      into the debate loop (1 cached call/side) — mock/stub-tested; live needs a key
- [x] D-4 Rounds: 5 (budget mode — disclosed in docs/sessions/session-01/SUMMARY.md)
- [x] D-5 Config format: YAML (assumed) vs. TOML

---

## Progress tracker (update as phases close)

- [x] Phase 0 — Bootstrap & safety rails
- [x] Phase 1 — Cross-cutting services
- [x] Phase 2 — Security primitives
- [x] Phase 3 — LLM provider layer
- [x] Phase 4 — Web search tool (live smoke test deferred to Phase 8)
- [x] Phase 5 — Agent hierarchy
- [x] Phase 6 — Orchestration
- [x] Phase 7 — SDK & interface
- [~] Phase 8 — Hardening, real run, audit (live run + demos + audit done;
      screenshots and live web-search smoke test pending — see notes)
- [~] Phase 9 — Documentation & submission (README + architecture.md +
      threat-model.md written; remaining items are manual submission steps:
      make repo public, tag the commit, create PDF, submit in Moodle)
