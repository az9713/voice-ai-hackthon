"""The voice agent's brain: Claude (Opus 4.8) + Sabre tools, manual agentic loop.

handle_query(text) is the one function Vocal Bridge's AI-agent mode calls per turn
(text in -> spoken reply out). It's plain Python with no voice dependency, so it's
fully unit-testable: feed it utterances, assert which Sabre tools it called.

    export ANTHROPIC_API_KEY=...     # needed to RUN (not to test the tool layer)
    export SABRE_BASE=http://localhost:8080
    python agent_brain.py            # type to the agent in a terminal REPL
"""
import json
import os

import anthropic

from sabre_tools import TOOLS, dispatch


def load_env(path=".env"):
    """Load .env into os.environ (no python-dotenv dep). Honored by the REPL and server.py."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
DEFAULT_MODEL = "claude-haiku-4-5"  # fast + cheap for voice; override with BRAIN_MODEL in .env

SYSTEM = """You are a hands-free travel assistant that speaks with the caller by voice.
You help travelers look up a booking, understand a problem (like a cancelled flight),
cancel segments, and rebook hotels — using the Sabre tools provided.

Rules:
- Replies are SPOKEN aloud. Keep them short and conversational — a sentence or two.
  No markdown, no bullet lists, no reading out raw IDs unless asked.
- Always look up the booking with get_booking before acting on it.
- NEVER cancel anything until the caller has clearly said yes. Confirm first, in plain words.
- Once the caller confirms a cancellation, call cancel_booking right away using the
  itemIds from get_booking — don't ask a second time.
- When you have the answer, say it plainly. Don't narrate which tools you're calling."""


def handle_query(user_text, messages=None, client=None, max_tokens=1024, model=None):
    """One conversational turn. Returns (reply_text, updated_messages, tool_names_called)."""
    client = client or anthropic.Anthropic()
    model = model or os.environ.get("BRAIN_MODEL", DEFAULT_MODEL)
    messages = messages or []
    messages.append({"role": "user", "content": user_text})
    tool_names = []

    while True:
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=SYSTEM, tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "tool_use":
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    tool_names.append(block.name)
                    out = dispatch(block.name, block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(out)[:8000],  # cap huge booking payloads
                    })
            messages.append({"role": "user", "content": results})
            continue

        reply = "".join(b.text for b in resp.content if b.type == "text")
        return reply, messages, tool_names


def _repl():
    model = os.environ.get("BRAIN_MODEL", DEFAULT_MODEL)
    print(f"Talk to the travel agent [model: {model}] (Ctrl-C to quit). Try: 'look up booking BQAUZG'\n")
    history = []
    try:
        while True:
            text = input("you > ").strip()
            if not text:
                continue
            reply, history, tools = handle_query(text, history)
            if tools:
                print(f"   [called: {', '.join(tools)}]")
            print(f"agent > {reply}\n")
    except (KeyboardInterrupt, EOFError):
        print("\nbye")


if __name__ == "__main__":
    _repl()
