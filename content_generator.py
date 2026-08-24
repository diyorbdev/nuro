"""
Uses Claude (Anthropic API) to:
1. Translate/simplify a research paper abstract into plain, engaging English
   suitable for Uzbek high schoolers (not native English speakers).
2. Generate one practical daily task based on that paper's finding.
"""

import os
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"  # always use this model per project convention

_client = None


def _get_client():
    """Lazily creates the Anthropic client only when actually needed."""
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def simplify_paper(paper: dict) -> str:
    """Turns a dense abstract into a short, simple, engaging summary."""
    prompt = f"""You are writing for Nuro, a Telegram channel for Uzbek high schoolers
(many are not native English speakers). Translate this research finding into
simple, engaging plain English. Requirements:
- Max 120 words
- No jargon; explain any technical term in plain words
- Start with why a student should care (the practical hook), not the study's title
- End with the one concrete takeaway
- Do NOT quote the abstract verbatim - fully rewrite it in your own words

Title: {paper['title']}
Authors: {paper['authors']}
Abstract: {paper['summary']}

Write only the final message, nothing else."""

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_daily_task(paper: dict, simplified_summary: str) -> str:
    """Generates one small, concrete, doable-today task based on the finding."""
    prompt = f"""Based on this research finding for high schoolers:

{simplified_summary}

Write ONE small, concrete task a student can do TODAY (not a vague suggestion).
Requirements:
- Max 40 words
- Must be specific and actionable (a number, a time, a clear action)
- Format: start with an action verb
- No jargon

Write only the task, nothing else."""

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def build_daily_post(paper: dict) -> str:
    """Combines everything into one formatted Telegram message."""
    summary = simplify_paper(paper)
    task = generate_daily_task(paper, summary)

    message = (
        f"🧠 *Today's Research* — {paper['topic'].title()}\n\n"
        f"{summary}\n\n"
        f"✅ *Today's Task:*\n{task}\n\n"
        f"📄 [Read the full paper]({paper['link']})"
    )
    return message
