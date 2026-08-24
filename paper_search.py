"""
Searches for recent, relevant research papers automatically.
Uses arXiv (free, no API key needed) for neuroscience/cognitive science papers,
and a simple keyword rotation so Nuro doesn't repeat the same topic every day.
"""

import feedparser
import random
import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "used_papers.json")

# Rotating topics relevant to Nuro's audience (study habits, sleep, focus, memory)
TOPICS = [
    "sleep and academic performance adolescents",
    "spaced repetition memory learning",
    "procrastination self-regulation students",
    "active recall retrieval practice",
    "attention focus study habits",
    "dopamine motivation learning",
    "screen time cognitive performance teenagers",
    "bedtime procrastination sleep habits",
    "growth mindset academic achievement",
    "exercise cognitive function students",
]


def _load_used():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def _save_used(used_ids):
    with open(STATE_FILE, "w") as f:
        json.dump(list(used_ids)[-200:], f)  # keep last 200 to avoid unbounded growth


def get_daily_paper():
    """
    Returns a dict with title, summary (abstract), authors, link for one paper
    the channel hasn't posted before. Falls back gracefully if arXiv is unreachable.
    """
    used = _load_used()
    topics = TOPICS[:]
    random.shuffle(topics)

    for topic in topics:
        query = topic.replace(" ", "+")
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue

        for entry in feed.entries:
            paper_id = entry.get("id", "")
            if paper_id and paper_id not in used:
                used.add(paper_id)
                _save_used(used)
                return {
                    "title": entry.get("title", "Untitled").replace("\n", " ").strip(),
                    "summary": entry.get("summary", "").replace("\n", " ").strip(),
                    "authors": ", ".join(a.name for a in entry.get("authors", [])) or "Unknown authors",
                    "link": entry.get("link", ""),
                    "topic": topic,
                }

    # Fallback if nothing new found across all topics
    return None
