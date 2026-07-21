# GTMScout — Design Note

## Project overview
GTMScout is a market-entry research assistant. You give it a country, a business type, and a budget,
and it returns a structured go/no-go brief: real economic data, a platform strategy, a budget split,
risks, next steps, and a citation for every fact. I built it to find out whether a small team of
specialized agents could produce grounded, checkable market advice instead of the confident guesses a
single model tends to give. The deliverable is a working end-to-end system: a FastAPI backend of
cooperating agents, a chat frontend, an evaluation harness, and this note.

## Problem and goals
Someone deciding where to expand asks a broad question, and answering it honestly needs several data
sources and several reasoning steps. Ask one model to do all of it in one prompt and you get fluent
text where you can't separate fact from guess, can't verify it, and can't fix one part without
disturbing another.

I set four goals I could actually measure against:
- **Grounding** — every number traces to a real source, never invented. *(Met: World Bank + live web, cited.)*
- **Self-correction** — the system catches and revises its own weak answers, not just returns the first draft. *(Met: a critic that can force a rewrite.)*
- **Interactive cost and speed** — single-digit seconds, a fraction of a cent per run. *(Met: ~8.8s, ~$0.002 per brief.)*
- **Provable** — works on a fixed case set, not only the demo. *(Met: 10/10 on the eval harness.)*

## Target audience
The end user is a founder, operator, or growth marketer weighing a new international market, someone
who would otherwise pay a consultancy or settle for a generic chatbot answer that makes the numbers
up. Their pain is speed and trust: they need a defensible first read fast, with sources they can
check. The second audience is whoever reads the code. The eval harness and the honest limitations
section exist partly for them.

## Scope and specifications
**In scope:** single-market briefs, side-by-side comparison of analyzed markets, and ranking across
candidate markets. **Out of scope:** financial or legal advice, anything illegal (blocked
deterministically before any model call), and sub-national markets.

The constraints I designed against, and the decisions they forced:
- **Facts from APIs, reasoning from the model.** World Bank for economics, Tavily for live signals,
  budget math recomputed in Python. The model phrases and reasons; it never sources a number.
- **Small agents with typed contracts.** About ten single-purpose agents with pydantic I/O, so each
  is testable and swappable in isolation. The cost is more model calls than one prompt would need.
- **An explicit graph.** The report loop is a LangGraph state machine: a planner picks tools, two I/O
  tools run concurrently, and a critic-to-revise cycle runs at most twice. The cost is that
  langchain-core adds weight to serverless cold starts.
- **Fail soft everywhere.** Per-indicator World Bank fallback, empty web results, a heuristic platform
  table, a cache that no-ops without a database. Nothing hard-fails; degraded output is flagged.

**Stack:** OpenAI `gpt-4o-mini`, FastAPI on Vercel (stateless), chat state in the browser, and an
optional Postgres + pgvector store for a cross-session research cache.

## Timeline and budget
The brief suggested 4–6 hours and "a smaller thing done well." I went past that and treated it as a
learning project, adding depth on stretch goals: self-correction, a RAG cache, fuzzy input handling,
injection defense, comparison and ranking modes, and deployment. A strictly to-spec version would be
the agent loop, three tools, error handling, the eval, and the README.

Budget here means cost, and I treated it as a design constraint rather than an afterthought. Every
agent call records its tokens and dollars, a full brief runs about $0.002, and the eval reports
per-report cost and latency, so a change that doubles spend shows up immediately.

Milestones, in the order they happened: single-shot pipeline, then conversation and intent routing,
then decisiveness and real budget re-runs, then the agent loop with reflection, then grounding via
live web plus the RAG cache, then country and edge-case hardening, then the eval harness, then the
LangGraph port.

## Beyond scope, next
Multi-model routing (a stronger model for the critic than the drafter), cache-first retrieval so the
pgvector store actually cuts web calls, faithfulness scoring with DeepEval on top of the structural
checks, auth and rate limiting before real traffic, and request tracing so a bad report can be
reproduced.

---
I used an AI assistant for background research and to move faster on boilerplate. The architecture,
the tradeoffs, and the decisions behind them are mine.
