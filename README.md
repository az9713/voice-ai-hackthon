# Voice Travel Agent — Sabre × Vocal Bridge

A hands-free travel assistant you **talk to**: it looks up a booking, explains a
problem (like a cancelled flight), cancels segments, and searches hotels — all
by voice. The voice layer is **[Vocal Bridge](https://vocalbridgeai.com)**; the
travel brain calls **Sabre's Agentic APIs** as tools, driven by **Claude**.

> **Inspiration.** This project was inspired by the **DeepLearning.AI Voice AI
> Hackathon — "The Complete Trip,"** powered by Sabre and Vocal Bridge, whose
> premise was *"Every AI agent can act. Few of them can speak."* It is an
> independent build, not a hackathon submission.

## Demo

<video src="https://github.com/az9713/voice-ai-hackthon/raw/main/demo.mp4" controls width="720"></video>

▶ If the player above doesn't load, [watch demo.mp4](https://github.com/az9713/voice-ai-hackthon/raw/main/demo.mp4) (~1.6 MB).

## How it works

```
🎤 browser (mic) ─► Vocal Bridge voice agent  (speech in/out, Web deploy)
       │  onAIAgentQuery(question)              ▲  speaks the reply
       ▼                                        │
  /api/brain (server.py) ─► agent_brain ─► Sabre tools ─► Sabre API
                              (Claude)                    (mock | real)
```

The voice agent delegates each question to a local **brain** (Claude + a manual
tool-use loop). The brain calls four Sabre tools — `get_booking`,
`cancel_booking`, `search_hotels`, `get_hotel_rates` — which POST to a single
configurable base URL (`SABRE_BASE`).

## Mock Sabre (contract-accurate)

Live Sabre data needs a provisioned **PCC** that isn't available on a self-serve
account, so this repo ships a **faithful mock** of the Sabre Agentic APIs. It is
generated from Sabre's **own published OpenAPI specs** (`extract_specs.py` →
`sabre_fixtures.json`) and replays Sabre's documented example payloads and error
envelopes at the **real endpoint paths**. Swapping to production is one env var:
`SABRE_BASE`. See **[DEVELOPMENT_JOURNEY.md](DEVELOPMENT_JOURNEY.md)** for the
full method and every design decision.

## Quick start

```bash
cp .env.example .env          # add ANTHROPIC_API_KEY and VOCAL_BRIDGE_API_KEY
pip install requests anthropic

python mock_sabre.py          # terminal 1: fake Sabre (stdlib, no deps)
python server.py              # terminal 2: voice backend → http://localhost:5000
```

Open `http://localhost:5000`, allow the mic, and say *"Look up booking BQAUZG."*
Prefer no browser? `python agent_brain.py` talks to the brain in the terminal.

## Tests

```bash
python test_sabre_tools.py    # tools vs the mock (no API key)
python test_brain_loop.py     # full agent loop, stubbed LLM (no API key)
python test_agent_brain.py    # real Claude picks the right tools (needs ANTHROPIC_API_KEY)
```

## Config (`.env`)

| Key | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | powers the brain |
| `VOCAL_BRIDGE_API_KEY` | the voice agent (from the agent's Develop tab) |
| `BRAIN_MODEL` | Claude model — defaults to `claude-haiku-4-5` (fast for voice) |
| `SABRE_BASE` | `http://localhost:8080` (mock) or real Sabre |
| `SABRE_USER_ID` | only needed for real Sabre |

## Stack

Python (stdlib HTTP, no web framework) · Claude (Anthropic SDK) · Vocal Bridge
(WebRTC/LiveKit) · Sabre Agentic REST APIs.

---

Full build narrative and decision log: **[DEVELOPMENT_JOURNEY.md](DEVELOPMENT_JOURNEY.md)**.
