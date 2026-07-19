"""Live web research via the Tavily API.

Tavily is built for AI agents: given a query it returns clean, summarized results
with source URLs. We call it with plain `requests` (no extra dependency).

Set TAVILY_API_KEY in the environment. If it's missing or a call fails, every
function degrades gracefully (returns empty results) so the pipeline never breaks —
it just runs without live web intel that turn.
"""
import os
from typing import Dict, List

import requests

TAVILY_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT = 12


def is_enabled() -> bool:
    return bool(os.getenv("TAVILY_API_KEY"))


def search(query: str, max_results: int = 5, search_depth: str = "basic") -> Dict:
    """
    Run one web search. Returns:
      {"success": True, "answer": str, "results": [{"title","url","content"}...]}
    or {"success": False, "error": ...} (callers should treat failure as "no intel").
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"success": False, "error": "TAVILY_API_KEY not set", "results": []}

    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": True,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content", "") or "")[:600],
            }
            for r in data.get("results", [])
        ]
        return {"success": True, "answer": data.get("answer", ""), "results": results}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


def research_market(country: str, business_type: str) -> Dict:
    """
    Run a small set of targeted searches for a market-entry brief and return
    de-duplicated snippets + sources.
    """
    queries = [
        f"{business_type} market in {country} 2024 2025: market size, top competitors, regulations",
        f"social media and digital advertising in {country} 2024: platform usage and consumer behavior",
    ]
    snippets: List[Dict] = []
    sources: List[Dict] = []
    seen_urls = set()
    any_ok = False

    for q in queries:
        res = search(q, max_results=4)
        if not res.get("success"):
            continue
        any_ok = True
        if res.get("answer"):
            snippets.append({"query": q, "answer": res["answer"]})
        for r in res["results"]:
            url = r.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                snippets.append({"query": q, "title": r["title"], "content": r["content"], "url": url})
                sources.append({"source": _domain(url), "detail": r["title"][:120], "url": url})

    return {
        "success": any_ok,
        "enabled": is_enabled(),
        "snippets": snippets[:12],
        "sources": sources[:6],
    }


def _domain(url: str) -> str:
    try:
        host = url.split("//", 1)[-1].split("/", 1)[0]
        return host.replace("www.", "")
    except Exception:
        return "web"
