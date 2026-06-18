"""Vendor-agnostic ontology builder.

Input: company name + capabilities (+ optional free text from decks/site).
Output: capability_map, expanded_keywords, mission_alignment, likely_competitors.

Uses Claude when ANTHROPIC_API_KEY is set (api.anthropic.com), else a deterministic
offline expansion so the feature is demonstrable without a key. The offline path is
what runs in this sandbox and in air-gapped deploys.
"""
import json
import os
import httpx

# Keyword expansion table for the offline path (graph/data-platform domain).
_EXPAND = {
    "graph database": ["graph database", "graph analytics", "property graph", "knowledge graph"],
    "knowledge graph": ["knowledge graph", "ontology", "semantic layer", "entity resolution"],
    "entity resolution": ["entity resolution", "record linkage", "identity", "deduplication", "link analysis"],
    "data fabric": ["data fabric", "data lake", "data integration", "data mesh"],
    "rag": ["rag", "retrieval augmented generation", "ml platform", "llm"],
    "link analysis": ["link analysis", "network analysis", "graph analytics"],
    "supply chain analysis": ["supply chain analytics", "logistics analytics", "graph analytics"],
    "ontology": ["ontology", "semantic layer", "knowledge graph"],
    "ai context": ["rag", "ml platform", "llm", "knowledge graph"],
}

_MISSIONS = {
    "readiness": ["supply chain analytics", "logistics analytics", "graph analytics", "data fabric"],
    "border": ["entity resolution", "identity", "link analysis", "record linkage"],
    "fin_crime": ["graph database", "entity resolution", "link analysis", "network analysis", "ontology"],
    "vet_care": ["knowledge graph", "case management", "rag", "data fabric"],
    "pop_health": ["data lake", "ml platform", "knowledge graph"],
}

PROMPT = """You are building a capability ontology for a technology vendor selling to government.
Company: {company}
Stated capabilities: {caps}
Extra context: {text}

Return ONLY minified JSON with keys:
  capability_map: array of normalised capability strings
  expanded_keywords: array of related procurement/search keywords
  mission_alignment: array of objects {{mission, rationale}} using only these mission ids: readiness, border, fin_crime, vet_care, pop_health
  likely_competitors: array of vendor names
No prose, no markdown."""


def _offline(company: str, capabilities: list[str], text: str) -> dict:
    caps = [c.strip().lower() for c in capabilities if c.strip()]
    keywords = set()
    for c in caps:
        keywords |= set(_EXPAND.get(c, [c]))
    align = []
    for mid, terms in _MISSIONS.items():
        hits = keywords & set(terms)
        if hits:
            align.append({"mission": mid, "rationale": f"matches {', '.join(sorted(hits))}"})
    align.sort(key=lambda a: a["rationale"], reverse=True)
    return {
        "capability_map": sorted({c for c in caps}),
        "expanded_keywords": sorted(keywords),
        "mission_alignment": align,
        "likely_competitors": [],
        "provider": "offline",
    }


async def build_ontology(company: str, capabilities: list[str], text: str = "") -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return _offline(company, capabilities, text)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": PROMPT.format(
                        company=company, caps=", ".join(capabilities), text=text[:4000] or "none")}],
                },
            )
            r.raise_for_status()
            txt = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
            data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
            data["provider"] = "anthropic"
            data.setdefault("mission_alignment", [])
            data.setdefault("expanded_keywords", [])
            data.setdefault("capability_map", capabilities)
            return data
    except Exception:
        out = _offline(company, capabilities, text)
        out["provider"] = "offline-fallback"
        return out
