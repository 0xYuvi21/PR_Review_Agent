# Project Description — AI Pull-Request Review Agent

## 1. What This Project Is

The AI Pull-Request Review Agent is an automated code-review system triggered when a GitHub pull request is opened or updated. It asynchronously analyzes the change, retrieves only the repository context needed by each review concern, runs specialist review agents in parallel, combines their structured findings, and either posts a review automatically or routes the case to a human reviewer.

The system automates repetitive review work while preserving human judgment for uncertain or high-consequence cases. It is selective rather than exhaustive: the goal is to surface findings worth a senior engineer's attention, not maximize comment volume.

### Core principles

1. **Selective, not exhaustive** — optimize for high-value findings.
2. **Grounded or silent** — never make claims about code that was not inspected.
3. **Agent-owned retrieval** — each specialist decides what repository context it needs.
4. **Structured everything** — agents exchange typed `Finding` objects, not prose.
5. **Evidence before claims** — every finding is tied to observed evidence.
6. **Proof of work** — LLM calls, tool calls, decisions, cost, latency, and confidence are observable.
7. **Slower-but-correct over fast-but-wrong** — failures should degrade safely.
8. **Autonomy is earned** — confidence, severity, and reversibility determine automation.

This follows the Antern production PR-review study's emphasis on selective review, specialist decomposition, grounded retrieval, structured findings, proof, reliability, and confidence-weighted HITL.

---

## 2. Goals and Design Principles

### Primary goals

- Automatically review GitHub pull requests.
- Reduce repetitive senior-review work.
- Analyze multiple review concerns concurrently.
- Ground every finding in the PR diff and repository evidence.
- Produce machine-readable review contracts.
- Automatically post sufficiently trusted reviews.
- Escalate uncertain or critical findings to humans.
- Maintain an auditable history of agent activity and decisions.
- Support many PRs concurrently through asynchronous queue-based execution.
- Keep models, retrieval, and workflow implementation replaceable.

### Review concerns

The initial system has four specialist concerns:

- **Security** — injection, authentication/authorization, secrets, unsafe deserialization, insecure data handling.
- **Quality** — correctness, logic errors, code smells, unnecessary complexity, maintainability.
- **Tests** — missing cases, edge conditions, brittle assertions, coverage gaps.
- **Docs** — missing/stale documentation, public API documentation, docstrings, comments, design rationale.

### Non-goals

The system does not attempt to:

- replace human judgment for high-consequence findings;
- comment without evidence;
- maximize comment count;
- put the entire repository into every prompt;
- hide failures behind successful-looking output;
- let an LLM make deterministic policy decisions that ordinary code can make.

---

## 3. Technology Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Workflow harness | **LangGraph** (`StateGraph`, `Send` fan-out, checkpointing) |
| LLM client | Provider-agnostic OpenAI-compatible wrapper |
| Embeddings | Configurable embedding model; initial `text-embedding-3-large`, 256 dimensions |
| Durable data spine | PostgreSQL + pgvector |
| Queue | Redis + ARQ |
| API / ingress | FastAPI |
| Frontend | Next.js dashboard |
| Tests | pytest + asyncio-compatible tooling |
| Validation | Pydantic |
| Observability | Application event spine + tracing |
| Runtime prompts | `agents.md` |

### Architectural decisions

**LangGraph is the workflow harness.** It owns graph execution, parallel specialist fan-out, typed state, checkpointing, and recovery. The application uses a harness-neutral workflow interface so other modules do not depend directly on LangGraph.

**Redis + ARQ handles asynchronous jobs.** GitHub webhooks are acknowledged quickly while review work runs asynchronously.

**PostgreSQL is the durable data spine.** Repository memory, review truth, and the event history live there. Redis remains the short-lived queue/checkpoint store.

---

## 4. System Architecture

```text
GitHub Pull Request
        │
        │ pull_request webhook
        ▼
┌──────────────────────┐
│ FastAPI Ingress      │
│ HMAC + idempotency   │
└──────────┬───────────┘
           │ enqueue
           ▼
┌──────────────────────┐
│ Redis + ARQ          │
│ Review Job Queue     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ LangGraph Workflow                   │
│                                      │
│  ┌──────────┬──────────┬──────────┐  │
│  │ Security │ Quality  │  Tests   │  │
│  │  Agent   │  Agent   │  Agent   │  │
│  └────┬─────┴────┬─────┴────┬─────┘  │
│       │          │          │         │
│       └── agent-owned retrieval ─────┘
│                  │
│                  ▼
│             Docs Agent
│                  │
│                  ▼
│              Aggregator
│                  │
│                  ▼
│            Confidence Gate
└──────────────────┬───────────────────┘
                   │
             ┌─────┴─────┐
             ▼           ▼
        Auto-post     Human/HITL
         GitHub         queue
```

### PR lifecycle

1. GitHub sends a `pull_request` webhook.
2. FastAPI verifies HMAC-SHA256.
3. The receiver checks `X-GitHub-Delivery` for idempotency.
4. The job is placed in Redis + ARQ.
5. An ARQ worker starts a LangGraph workflow.
6. Four specialists run concurrently.
7. Each specialist retrieves its own relevant repository context.
8. Each returns `Finding[]`.
9. The aggregator merges and deduplicates findings.
10. Overall confidence is computed.
11. The autonomy/HITL policy determines the route.
12. Low-confidence/critical cases enter human review.
13. Approved reviews are posted to GitHub.
14. Significant actions are written to the event spine.

### Concurrency model

- **Across PRs:** Redis + ARQ enables multiple workers and horizontal scaling.
- **Within a PR:** LangGraph fans specialists out concurrently and joins them before aggregation.

---

## 5. Agent Architecture

### Specialist agents

Each specialist receives the PR diff and workflow state, then decides what additional evidence it needs.

```text
PR diff
  │
  ▼
Specialist Agent
  ├── semantic repository search
  ├── exact/keyword search
  ├── file/symbol inspection
  ├── related test lookup
  └── relevant history/review lookup
  │
  ▼
Evidence
  │
  ▼
Finding[]
```

Security, quality, testing, and documentation reviews require different evidence. Therefore the workflow coordinates **when agents run**, while agents own their detailed reasoning and retrieval decisions.

### Aggregator

The aggregator:

- collects specialist findings;
- deduplicates overlapping findings;
- preserves strongest evidence/confidence;
- records agreement;
- computes `overall_confidence`;
- applies the HITL policy;
- never invents findings.

---

## 6. Data Architecture

### Memory lane

`code_chunks` stores repository chunks, embeddings, searchable text, repository/path metadata, and freshness information.

Retrieval combines:

- semantic/vector search;
- keyword/full-text search.

Vector search captures semantic similarity; exact search captures identifiers such as functions, classes, configuration keys, and error codes.

### Truth lane

Durable review state is stored in:

- `pr_review_records`
- `finding_records`
- `hitl_reviews`
- `hitl_feedback`

### Time lane

`agent_events` is an append-only event history for:

- workflow spans;
- LLM calls;
- tool calls;
- decisions;
- escalations;
- tokens;
- cost;
- latency;
- confidence;
- outcomes.

### Queue/checkpoint lane

Redis is used for:

- ARQ jobs;
- short-lived queue state;
- LangGraph checkpointing.

Redis is not the durable source of truth.

---

## 7. Contracts

### Finding

```python
class Finding(BaseModel):
    agent_type: Literal["security", "quality", "tests", "docs"]
    severity: Literal["CRITICAL", "MAJOR", "MINOR", "INFO"]
    category: str
    summary: str
    file_path: str
    line_start: int
    line_end: int | None = None
    suggestion: str | None = None
    confidence: float
    rationale: str
```

### Review

```python
class Review(BaseModel):
    findings: list[Finding]
    overall_confidence: float
    route: Literal["post", "human"]
```

### Contract rules

- Specialist outputs are structured JSON/Pydantic objects.
- Confidence represents calibrated uncertainty.
- Rationale must cite evidence actually available to the specialist.
- Locations should identify affected code precisely.
- Aggregation operates on structured data, not free-form prose.

---

## 8. Autonomy & HITL

| Condition | Action |
|---|---|
| `overall_confidence >= 0.7` and no CRITICAL | Post automatically |
| `overall_confidence < 0.7` | Human approval queue |
| Any CRITICAL | Human escalation regardless of confidence |
| Developer disputes a posted finding | Dispute flow + feedback |

The threshold is configurable and must be calibrated through evaluation rather than treated as an immutable truth.

The system should begin conservatively and earn autonomy through observed reliability.

---

## 9. Repository Structure

```text
pr-review-agent/
├── AGENTS.md
├── agents.md
├── README.md
├── .env.example
├── pyproject.toml
├── docs/
│   ├── adr/
│   └── threat_model.md
├── migrations/
├── scripts/
├── src/
│   ├── agents/
│   ├── api/
│   ├── auth/
│   ├── core/
│   ├── data/
│   ├── database/
│   ├── economics/
│   ├── evaluation/
│   ├── hitl/
│   ├── integrations/
│   ├── job_queue/
│   ├── memory/
│   ├── models/
│   ├── observability/
│   ├── orchestrator/
│   ├── reliability/
│   ├── security/
│   ├── tools/
│   ├── webhook_receiver/
│   └── main.py
├── tests/
└── frontend/
```

Detailed coding constraints are in `AGENTS.md`; runtime LLM prompts are in `agents.md`.
