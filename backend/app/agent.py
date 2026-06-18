"""Capture-analyst agent.

Provider resolution order:
  1. ANTHROPIC_API_KEY set            -> Anthropic Messages API
  2. OLLAMA_HOST set                  -> local Ollama (matches air-gapped deploys)
  3. neither                          -> deterministic offline analyst

The feed is passed as grounding context so answers reference live opportunities.
"""
import os
import httpx

SYSTEM = (
    "You are a UK/EU public-sector capture analyst inside a procurement-intelligence "
    "tool called Chancery. Be concise, concrete and tactical. Reference the live "
    "opportunity feed where relevant. Favour sovereignty, auditability and data-residency "
    "as competitive levers against US-hosted incumbents."
)

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def _feed_context(opps) -> str:
    rows = [
        f"{o.ref} | {o.title} | {o.agency} | £{o.value:,} | closes {o.close} | incumbent {o.incumbent}"
        for o in opps
    ]
    return "LIVE FEED:\n" + "\n".join(rows)


async def _anthropic(question: str, context: str) -> str:
    key = os.environ["ANTHROPIC_API_KEY"]
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 1000,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": f"{context}\n\nQUESTION: {question}"}],
            },
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


async def _ollama(question: str, context: str) -> str:
    host = os.environ["OLLAMA_HOST"].rstrip("/")
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{host}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"{context}\n\nQUESTION: {question}"},
                ],
            },
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "").strip()


def _offline(question: str, opps) -> str:
    q = question.lower()
    hit = next((o for o in opps if any(w in q for w in o.title.lower().split() if len(w) > 4)), None)
    if hit is None and opps:
        hit = max(opps, key=lambda o: o.value)
    if hit is None:
        return "No opportunities in the feed yet. Run an ingest first."
    days = (hit.close - __import__("datetime").date.today()).days if hit.close else None
    new = "None" in hit.incumbent
    return (
        f"Working from the live feed:\n\n"
        f"• {hit.agency} has a £{hit.value:,} requirement ({hit.ref})"
        + (f", closing in {days} days.\n" if days is not None else ".\n")
        + (f"• No incumbent — a genuine open field.\n" if new
           else f"• Incumbent: {hit.incumbent}. Position as a credible challenger, not a like-for-like swap.\n")
        + "• Decisive axis: data residency and auditability. Lead there.\n\n"
        "(Offline analyst — set ANTHROPIC_API_KEY or OLLAMA_HOST for live reasoning.)"
    )


async def ask(question: str, opps) -> tuple[str, str]:
    """Returns (answer, provider)."""
    context = _feed_context(opps)
    try:
        if os.getenv("ANTHROPIC_API_KEY"):
            return (await _anthropic(question, context)) or _offline(question, opps), "anthropic"
        if os.getenv("OLLAMA_HOST"):
            return (await _ollama(question, context)) or _offline(question, opps), "ollama"
    except Exception as e:  # network / auth / model error -> graceful fallback
        return _offline(question, opps) + f"\n\n[provider error: {type(e).__name__}]", "offline"
    return _offline(question, opps), "offline"
