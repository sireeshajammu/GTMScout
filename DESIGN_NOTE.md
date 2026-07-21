# GTMScout — Design Note

## What it is
A market-entry research assistant. You give it a country, a business type, and a budget
("fintech app in Brazil, $20k"), and it returns a structured go/no-go brief: real economic
data, a platform strategy, a budget split, risks, next steps, and a citation for every fact.
The interesting part isn't the output format, it's that answering this well needs several
steps and several data sources, so a single model call can't do it honestly.

## The core decision: many small agents behind an explicit graph
I started with one big prompt and threw it out. With one call you can't tell which sentence is
a fact and which is a guess, you can't check the work, and you can't fix one part without
risking another. So the system is ~10 single-purpose agents (intake, planner, data, research,
platform, strategy, critic, deep-dive, plus comparison/ranking for multi-market questions),
and the report path is a LangGraph `StateGraph` that decides what runs and checks the result.

The flow for a report: **plan → gather → synthesize → critique → (revise) → deep-dive →
assemble.** The planner picks which tools are worth calling. Gather runs the World Bank fetch
and the web search concurrently, then ranks platforms off the research. Strategy writes the
verdict. The critic checks it. If the critic finds unsupported claims or confidence lands below
70, a conditional edge routes back to a revise node that re-runs strategy with the criticism
injected, then re-checks. That loop is capped at two passes so it can't spin.

## The principle I'd defend first: facts and reasoning are separate
Any real number comes from a real source, never the model. Population and GDP come from the
World Bank API. Competitors and market signals come from live web search (Tavily). The model
only reasons over numbers it's handed, and the budget math is recomputed in Python after the
LLM answers so the allocation always sums to the actual budget. This is the single biggest
thing keeping the output from being confident nonsense.

## Self-correction is a real loop, not asking twice
The agent that writes the recommendation and the one that critiques it are separate calls with
separate prompts, and only the critic can force a rewrite. The critic returns flags plus a
confidence delta; the orchestrator combines that into an effective confidence and decides
whether to revise. If the reason confidence is low is that research was skipped, revise goes
and gets the research first, then rewrites. In evaluation this fired on nearly every case,
which is honestly a sign the confidence floor is tuned too strict, not a badge of quality.

## Everything degrades instead of breaking
Each World Bank indicator is fetched independently, so one failure falls back to a curated
figure and is flagged, rather than dumping the whole request to cached data (a real bug I
fixed). Web search and the vector cache are both optional; missing keys mean fewer findings,
not a crash. The platform ranker prefers platforms the live research names as locally relevant
(so KakaoTalk shows up for Korea), and falls back to a hand-tuned table when research is thin.

## RAG, injection, evaluation
- **RAG** is a pgvector cache of past research *findings*, keyed by country and business, shared
  across sessions. It's a cheap-recall layer beside the live search, not the primary retrieval,
  because for market data the ground truth is live. Today it augments the web call rather than
  replacing it, so it isn't saving API calls yet.
- **Prompt injection** from web pages is handled in layers: a deterministic scanner drops
  snippets with injection markers, surviving content is wrapped in tags the prompt marks as
  data-not-instructions, output is schema-constrained, and that agent has no side effects, so a
  bypass can only skew text. It's defense in depth, not a proof.
- **Evaluation** is 10 cases with deterministic pass/fail: structure, routing, directional
  verdict, tool-call success, self-correction rate, latency, cost. Last run was 10/10, ~8.8s and
  ~$0.002 per report. It does not judge prose factuality; that would need an LLM judge or a human.

## Where it stops, and why
It's on `gpt-4o-mini`, stateless behind FastAPI on Vercel, with chat state in the browser.
Known gaps I'd close before calling it production: the two web searches run sequentially and can
approach the serverless timeout; there's no rate limiting or spend cap; the critic floor needs
calibrating against labeled data; the planner commits to a tool set upfront instead of choosing
tools interactively as it sees results. Those are deliberate scope cuts, not oversights.
