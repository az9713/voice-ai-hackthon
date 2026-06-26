# Development Journey — Voice Travel Agent (Sabre × Vocal Bridge)

> **Purpose of this document.** A faithful record of how this project was built —
> the origin, the onboarding of both platforms, the architecture, and **every
> decision fork with its reasoning and trade-offs**. It is written to be read
> later as a reference when discussing whether the development decisions were
> good ones. Where a choice was a judgement call, the alternatives and the
> "why" are recorded so they can be second-guessed with full context.
>
> **How to read it.** Sections 1–4 are context and research. Section 5–7 cover
> onboarding both vendors. Section 8 is the central architecture decision.
> Section 9 documents the mock — the most consequential build choice — in
> detail. Sections 10–13 cover the agent, model, tests, and voice wiring.
> Section 16 is a compact **decision log** suitable for a review meeting.

---

## 1. Origin — the hackathon brief

The seed was the **DeepLearning.AI Voice AI Hackathon: "The Complete Trip,"**
powered by **Sabre** and **Vocal Bridge** (Saturday, July 18 2026, Mountain
View, CA; application-only, in-person).

The brief's thesis: *"Every AI agent can act. Few of them can speak."* Booking
travel is manual and disconnected — flight, hotel, ground transport, dining each
live in a different app. The challenge: use **Sabre's travel APIs** + **Vocal
Bridge's voice layer** to pull a whole trip into a single voice conversation —
booked and managed by a voice agent. Submissions had to use both. Prizes
$5,000; judges included Andrew Ng.

The canonical example scenarios: an agent that calls the airline, waits on hold,
and rebooks a cancelled flight; or one that resolves a hotel snafu abroad by
voice. **This "booking-snafu over the phone" scenario became the project's
guiding use case.**

## 2. Decision Fork #0 — not actually competing

Early on, the developer clarified they were **not** taking part in the hackathon
— building this for the challenge and for fun. This is recorded first because it
**changed the entire Sabre credential strategy** (see §6). At a hosted
hackathon, Sabre staff hand out provisioned credentials; for a solo hobby build
that path is gone, which is what later forced the mock.

## 3. Research phase — reading the source docs

A `README.txt` pointed at four documentation URLs:

1. `vocalbridgeai.com/docs/developer-guide`
2. `developer.sabre.com`
3. `developer.sabre.com/.../agentic-api/1.0/`
4. `developer.sabre.com/guide/overview/`

**Fork #1 — static fetch vs real browser.** A plain HTTP fetch of these URLs
returned only the JavaScript app shell (both sites are client-rendered SPAs;
Vocal Bridge's guide also sits behind a login). The docs were therefore read by
**driving a real logged-in Chrome session** and extracting rendered text.

**Nuance — the content filter.** The browser tool's output filter repeatedly
blocked extractions of code blocks (flagging "cookie/query string data,"
triggered by example tokens and `key=value&...` shapes in the docs). The
workaround was to **sanitize before returning** — redacting long token-like
strings and, where necessary, stripping digits and `=&?` punctuation. This
preserved method and event names (the part that mattered) while removing the
patterns that tripped the filter. This is why some extracts in the transcript
show `#` in place of numbers.

## 4. What the research established

**Vocal Bridge.** Voice agents embedded over **WebRTC**, built on **LiveKit**,
sub-second latency. `vb_`-prefixed API keys; a backend mints short-lived
connection tokens (`POST /api/v1/token` with an `X-API-Key` header). SDKs for
JS, Python, React, Flutter. Critically, it exposes **two distinct ways** for a
voice agent to call tools — see §8.

**Sabre Agentic APIs.** A set of REST APIs re-shaped for LLM function-calling
(smaller/flatter payloads, semantically-rich OpenAPI specs, actionable error
messages). The Agentic collection has **four** APIs: **Booking Management**,
**Hotel Search**, **Hotel Rates**, **Hotel Price Check**. Auth is **sessionless
OAuth bearer tokens** (7-day life) over REST.

## 5. Sabre auth — the token model

Two token-creation paths were identified:

| | grant_type | Credentials in auth header | Self-serve? |
|---|---|---|---|
| **OAuth Token Create v2** | `client_credentials` | EPR encoded into the user ID | **Yes** (free Developer Hub) |
| OAuth Token Create v3 | `password` | ClientId (app), EPR in body | No — needs ClientId/Secret |

**Fork #2 — v2 vs v3.** Chose **v2**: it works with a self-serve account and
needs no ClientId/Secret. The credential string is built with Sabre's nested
base64 recipe: `base64( base64(userID) : base64(password) )`.

## 6. Sabre onboarding — and the wall

1. **Created a free Sabre Developer Hub account.**
2. **"Where's the API key?" (nuance).** Sabre has **no single API key**. The
   token credentials are generated only when you create an **Application** under
   *My Account → Applications*. Doing so produced:
   - User ID of the form `V1:<id>:DEVCENTER:EXT` (the `DEVCENTER` group marker
     is the key detail — see the PCC wall below)
   - a separate Password (the secret)
3. **Token flow built (`sabre_token.py`).** Implements the v2 base64 recipe and
   posts to `api.cert.platform.sabre.com/v2/auth/token`. A **self-test** verifies
   the base64 construction against Sabre's own documented example before any
   network call. Result: **HTTP 200**, a real bearer token, `expires_in: 604800`
   (7 days). Auth fully working.
4. **Decision Fork #3 — the PCC wall (the pivotal moment).** Calling the **real
   Agentic Hotel Rates API** with that token returned **HTTP 200** but an
   application error: `INVALID_PCC. LENGTH OF PCC IS GREATER THAN 5 CHARACTERS`.
   The token's "group" field is `DEVCENTER` (9 chars), a generic sandbox marker
   — **not a real 5-char Pseudo City Code**. Interpretation, confirmed
   empirically:
   - **Auth: works.** (no 401)
   - **Agentic API reachable: works.** (no 403 — the request reached business logic)
   - **Blocker: no provisioned PCC** → cannot return live data.

   Because the developer is not at the hackathon (Fork #0), there is no easy way
   to get a real PCC (normally requires a Sabre account manager / contract).
   **This forced the decision to mock Sabre** (§9) rather than chase credentials.

## 7. Vocal Bridge onboarding — and the agent

1. **Created an account** (gated by phone verification — a one-time human step).
2. **Created an agent** via the *New Agent* form. Settings of note:
   - **Style:** started Gemini, settled on **Chatty (low latency)** — "ideal
     when you only need 1–2 tools," which fits this small tool set.
   - **Deploy to: Decision Fork #4 — Web only.** Two reasons: (a) the on-screen
     note says phone deployment needs a paid plan or partner credits — Web is the
     free tier; (b) the chosen architecture (§8) connects over the **web data
     channel**, not telephony. *"Web only"* is a **delivery channel**, not a
     different kind of agent — it is still a voice agent; the audio simply
     arrives over the web instead of a phone call. (This distinction caused a
     terminology confusion later — "web agent vs voice adapter" — that is purely
     vocabulary, not architecture.)
   - **Integration mode: AI agent** (delegates reasoning to our app — see §8).
3. **"Nowhere I see the API key" (nuance).** The `vb_` key does not exist until
   the agent is **created**; it then lives on the agent's **Develop tab**
   (*Agent API keys*), and account-level keys under Dashboard → API Keys. The
   Develop tab also offers **"Copy guide"** — the full, agent-specific developer
   guide for pasting into an AI coding assistant.

## 8. The central architecture decision — how the voice agent calls Sabre

Vocal Bridge offers two tool-calling models. **This was the most important
architecture fork (Fork #5).**

| | **Custom HTTP API Tools** | **AI Agents mode** (chosen) |
|---|---|---|
| Who calls Sabre | VB **cloud** agent calls the REST endpoint directly | **Your app** answers each question; you call Sabre |
| Reasoning / tool choice | VB's built-in Claude ("Background AI") | **Your own** Claude call, in your code |
| Localhost mock | ✗ needs a public HTTPS tunnel (VB cloud can't reach localhost) | ✓ your app makes the call — localhost works |
| Testability of decisions | hard (logic lives in VB cloud) | **easy — plain Python, unit-testable** |
| Code to write | least (config only) | a small brain + a data-channel bridge |

**Chose AI Agents mode.** Rationale: it runs entirely against a `localhost`
mock with **no tunnel exposing the machine**, the "brain" is plain Python so it
is **fully auto-testable**, and we own the tool-calling logic (the explicit ask
was to "automate the tests" and control "how the calls are generated"). The
protocol: the voice agent sends a `query_agent`/`onAIAgentQuery` event over the
LiveKit data channel; our app answers; VB speaks the answer.

```
🎤 browser (mic) ─► Vocal Bridge voice agent (STT/TTS, Web deploy)
       │  onAIAgentQuery(query)            ▲  speaks the reply
       ▼                                   │
  /api/brain (server.py) ─► agent_brain ─► Sabre tools ─► Sabre (mock | real)
                              (Claude)
```

The trade-off accepted: more code than the config-only path, and we don't lean
on VB's built-in Claude. The win: local, testable, owned.

## 9. The mock Sabre API — faithful replication

The PCC wall (Fork #3) meant Sabre had to be stood in for. The guiding
principle was **contract accuracy**: the mock must be indistinguishable from
real Sabre at the level of paths, request shapes, response shapes, and error
envelopes — so that the agent code, request bodies, auth header, and response
parsing are all *exactly* what production will use.

### 9.1 How faithful replication was achieved (the method)

1. **Found the specs are public.** Although the doc viewer is a login-walled
   SPA, the underlying OpenAPI files are served at
   `developer.sabre.com/api/v1/products/rest-api/<slug>/v1/_attachments/spec.yml`
   **with no auth** — discovered by inspecting the page's own network resource
   list. `curl` fetched them directly.
2. **Downloaded all four real OpenAPI specs** (Booking Management ≈ 450 KB,
   Hotel Search ≈ 43 KB, Hotel Rates ≈ 33 KB, Hotel Price Check ≈ 33 KB).
3. **Parsed them programmatically** (`extract_specs.py`, PyYAML). For each API it
   extracts:
   - the **real server base URL** (e.g. `https://api.cert.platform.sabre.com/v1/trip/orders`
     for Booking Management, `/v1/hotels` for the hotel APIs);
   - every **operation's real path + method** (all RPC-style `POST`s, e.g.
     `/getBooking`, `/createBooking`, `/modifyBooking`, `/cancelBooking`,
     ticket ops, `/hotelSearch`, `/getHotelRates`, `/checkHotelRate`);
   - the spec's **own documented example request and response payloads**,
     resolving `$ref` pointers into `components/examples`.
   Output: **`sabre_fixtures.json`** — real paths + real example data.
4. **Served them back** (`mock_sabre.py`, Python **stdlib only**). Routes are
   built dynamically from the fixtures (so coverage tracks the real contract),
   each returns Sabre's **own example response verbatim**, with the **real error
   envelope** `{timestamp, errors:[{category, type, description}]}` and light
   request validation (e.g. missing `confirmationId` → real error shape).

**Why this is "faithful," concretely:** the example payloads, error envelope,
URL structure, and request bodies are Sabre's, taken from Sabre's published
specs — not invented. The error envelope was additionally **cross-checked
against the live response** we got from the real `getHotelRates` (the
`INVALID_PCC` error in §6 has exactly this shape).

### 9.2 Decision Fork #6 — faithful *replay* vs *stateful* mock

The mock is a **faithful replay, not stateful**: `cancelBooking` does **not**
mutate what a later `getBooking` returns. This was a deliberate choice. Making
the mock stateful would require **inventing cross-call data that isn't Sabre's**
— which would undercut the whole point of "match exactly." Instead, the example
payloads are **user-editable** (`sabre_fixtures.json` is plain JSON), so any
scenario (e.g. a pre-cancelled flight) can be scripted by hand without
fabricating API behavior. The ceiling is named in the code comment; the upgrade
path (an in-memory store) is noted for if a live-mutating demo is ever wanted.

### 9.3 Other mock nuances

- **Fork #7 — stdlib over dependencies.** The mock (and later the web server)
  use Python's `http.server` rather than Flask, and a 6-line `.env` parser rather
  than `python-dotenv` — **zero new dependencies**.
- **`checkHotelRate` returns 501.** Its spec carries no example payload; rather
  than fabricate one, the mock honestly returns `NO_EXAMPLE_IN_SPEC`. (Silent
  fabrication was explicitly avoided.)
- **The seam.** A single `SABRE_BASE` environment variable is the entire
  swap-to-production seam: point it at `http://localhost:8080` (mock) or
  `https://api.cert.platform.sabre.com` (real, plus a real token + a provisioned
  PCC). No agent code changes.

## 10. The brain and the tools

- **`sabre_tools.py`** — four typed tools (`get_booking`, `cancel_booking`,
  `search_hotels`, `get_hotel_rates`) that POST to the **real Sabre paths**
  under `SABRE_BASE`, plus their Claude tool schemas. The schemas are
  prescriptive about *when* to call each tool (good practice for tool-use).
- **`agent_brain.py`** — `handle_query(text) → (reply, messages, tool_names)`,
  a **manual agentic loop** (Claude `messages.create` → execute any `tool_use`
  → feed results back → repeat until `end_turn`). The system prompt makes
  replies short/spoken, requires a lookup before acting, and **requires explicit
  confirmation before cancelling**. A terminal REPL lets you talk to it by
  typing before any voice exists.

## 11. Decision Fork #8 — model selection

- Started on **`claude-opus-4-8`** (the Claude API guidance default).
- Then made the model **configurable via `.env`** (`BRAIN_MODEL`), defaulting to
  **`claude-haiku-4-5`**. Rationale: for a *voice* agent, the lag between "you
  stop talking" and "the agent speaks" matters; Haiku is fastest/cheapest and —
  as the tests later proved — **smart enough for this 4-tool agent** with no
  observable quality loss. Sonnet/Opus remain a one-line override for harder
  decisions.
- **Dropped `thinking: {type:"adaptive"}`.** It adds a reasoning pause (bad for
  voice), isn't supported on Haiku 4.5, and isn't needed for this small tool set.
  Omitting `thinking` is valid on every model, so switching `BRAIN_MODEL` up to
  Opus/Sonnet still works.

## 12. Testing strategy — "automate the tests / generate the calls"

Three layers, deliberately separating what needs an API key from what doesn't:

| Test | LLM? | Proves |
|---|---|---|
| **`test_sabre_tools.py`** | none | Every tool hits the real Sabre paths; calls **generated from the fixtures**; real error envelope on missing fields |
| **`test_brain_loop.py`** | **stubbed Claude** | The full agentic loop wiring — a `tool_use` really executes against the mock and threads the result back — **no API key needed** |
| **`test_agent_brain.py`** | real Claude | Scripted conversations assert the model picks the right tool **and speaks the right facts** |

**"How are the calls generated?"** — two senses, both captured: (a) at runtime,
**Claude's tool-use** turns natural language into Sabre calls; (b) for tests,
calls are **generated from `sabre_fixtures.json`** so coverage tracks the real
contract.

**Decision Fork #9 — the cancel-test lesson.** The cancel test first failed:
Haiku looked up the booking but didn't cancel. Investigation (printing the
agent's actual turns) showed the booking has **four** flights, so "cancel the
flight" is genuinely ambiguous — Haiku **correctly** asked "which one — all
four?" The fix was to the **test**, not the model: make it a realistic
**multi-turn** exchange with an unambiguous confirmation. It then passed
("All four flights have been cancelled"). **Conclusion recorded for review:
Haiku's caution was correct behavior; the model is adequate; the test was
under-specified.** A good reminder not to "fix" a model for a test's bug.

## 13. The voice adapter

- **`server.py`** (stdlib) — serves the page, **proxies the VB token**
  (`/api/voice-token`, keeping the `vb_` key server-side), and runs the brain
  (`/api/brain`, with per-session history).
- **`.env`** — holds `ANTHROPIC_API_KEY`, `VOCAL_BRIDGE_API_KEY`, `BRAIN_MODEL`,
  `VOCAL_BRIDGE_URL`, `SABRE_BASE`. **The Anthropic key never reaches the
  browser** — the browser calls `/api/brain`; Python makes the Claude call. A
  consistency fix was applied so **every** entry point (server, REPL, brain
  test) loads `.env` — no shell `export` needed.
- **`voice.html`** — browser voice client using the VB JS SDK. The AI-agent
  bridge uses the **confirmed** API (extracted from the docs, not guessed):
  `vb.onAIAgentQuery(async (query) => { return await askBrain(query); })` — the
  SDK speaks the return value automatically.
- **Remaining runtime unknown:** the SDK's CDN import path
  (`https://esm.sh/@vocalbridgeai/sdk`) — only verifiable by loading the page;
  the Develop-tab "Copy guide" has the authoritative path if it 404s.

## 14. The demo video

`demo.mp4` (a screen recording of the working agent) was **93 MB** — too heavy
for a README. **Decision Fork #10 — cut from the original, not the compressed
file.** When asked to trim the first 40 seconds *and* compress, the trim was
done from the **original** source in a **single encode** rather than
re-compressing the already-compressed file, to avoid stacking a second round of
generation loss. Settings: H.264, CRF 28, downscaled to 1280-wide, AAC audio
kept (it's a *voice* demo), `+faststart` for inline playback. Result: **93 MB →
1.6 MB** (98% smaller), 69.6 s, audio intact.

## 15. File inventory

| File | Role |
|---|---|
| `sabre_token.py` | Real Sabre v2 OAuth token (base64 recipe + self-test) |
| `extract_specs.py` | Parses the 4 real OpenAPI specs → `sabre_fixtures.json` |
| `sabre_*.yml` | The four real Sabre OpenAPI specs (downloaded) |
| `sabre_fixtures.json` | Real paths + Sabre's own example payloads (editable) |
| `mock_sabre.py` | Contract-accurate fake Sabre (stdlib; faithful replay) |
| `sabre_tools.py` | The 4 agent tools + Claude tool schemas |
| `agent_brain.py` | Claude agentic loop + terminal REPL |
| `server.py` | Voice-adapter backend (token proxy + brain + page) |
| `voice.html` | Browser voice client (VB SDK, AI-agent mode) |
| `.env` / `.env.example` | Secrets + config (gitignored) |
| `test_sabre_tools.py` / `test_brain_loop.py` / `test_agent_brain.py` / `test_server.py` | The automated suite |
| `demo.mp4` | Compressed, trimmed demo (1.6 MB) |

## 16. Decision log (for review)

| # | Decision | Chosen | Alternative(s) | Why |
|---|---|---|---|---|
| 0 | Compete in hackathon? | No (hobby) | Compete | Personal; reframed the credential strategy |
| 1 | Read SPA docs | Real browser | Static fetch | SPAs render client-side / login-walled |
| 2 | Sabre token version | v2 | v3 | v2 is self-serve, no ClientId/Secret |
| 3 | Live Sabre vs mock | **Mock** | Chase a PCC | DEVCENTER creds have no real PCC; no hackathon staff |
| 4 | VB deployment | **Web only** | Phone / Phone+Web | Free; matches the web data-channel architecture |
| 5 | Tool-calling model | **AI Agents mode** | Custom HTTP Tools | Localhost-friendly, testable, owned logic |
| 6 | Mock fidelity model | **Faithful replay** | Stateful mock | Avoid inventing non-Sabre data; keep "match exactly" |
| 7 | Dependencies | **Stdlib only** | Flask + dotenv | Zero install friction |
| 8 | Brain model | **Haiku 4.5 (configurable)** | Opus 4.8 fixed | Voice latency; proven adequate; `.env` override |
| 8b | Thinking | **Off** | Adaptive thinking | Latency + Haiku support; not needed for 4 tools |
| 9 | Cancel-test failure | Fix the **test** (multi-turn) | "Fix" the model | The model's caution was correct |
| 10 | Demo trim | Cut from **original** | Re-compress compressed | Avoid double generation loss |

## 17. Open questions & limitations (honest)

- **Sabre stays mocked.** Real Agentic data needs a provisioned **PCC** (proven
  by the live `INVALID_PCC`). The mock is contract-accurate, so "full testing"
  means the complete voice → brain → Sabre-shaped-API loop with realistic data,
  **not** live bookings.
- **Mock is replay, not stateful** — cross-call effects (cancel then re-fetch)
  are not reflected; edit fixtures to script scenarios.
- **`checkHotelRate`** has no spec example → mock returns 501.
- **VB SDK import path** (`esm.sh/@vocalbridgeai/sdk`) is runtime-unverified.
- **One model, one trip** — the agent currently covers lookup / cancel / hotel
  search & rates. Flights are not a first-class Agentic op in the beta set
  (the collection is booking + hotels); flight rebooking would go through
  `modifyBooking` / `createBooking`.

## 18. Path to production (what would change)

1. Obtain real Sabre credentials **with a provisioned PCC** (account manager).
2. Set `SABRE_BASE=https://api.cert.platform.sabre.com` and have `sabre_tools`
   use the **real token** (already implemented in `sabre_token.py`).
3. Confirm the four Agentic endpoints accept the token + PCC (expect the
   `INVALID_PCC` error to disappear).
4. Verify the VB SDK import path; finalize `voice.html`.
5. Decide whether to keep the local brain (AI Agents mode) or move tool-calling
   into VB's **Custom HTTP API Tools** (would need the mock/real API publicly
   reachable). The current design makes either possible — the tools are the
   same; only the caller changes.
