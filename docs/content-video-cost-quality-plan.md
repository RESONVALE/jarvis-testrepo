# /Content and /Video: lower input cost, same quality, learning built in

Status: **draft proposal. No production code was changed.**

## 0. Read this first: what this plan is based on

The task asked for four things:

1. Make every input to /Content and /Video better and cheaper, without
   lowering quality.
2. Make learning a required part of how both agents work.
3. Give both agents more references and inputs.
4. Find tools, extensions and external databases that improve quality, cost
   and delivery time.

**The /Content and /Video code is not available to the Dev agent.** This
repository (`RESONVALE/jarvis-testrepo`) contains only the `greeter` practice
package. The agent's credentials get "Repository not found" for every other
RESONVALE repository it tried (`jarvis`, `jarvis-core`, `content`, `video`,
`jarvis-content`, `jarvis-video`, `jarvis-agents`, `agents`, `resonvale`).
The same gap is noted in `docs/jarvis-improvement-plan.md` on branch
`jarvis/20261024-2057-investigate-jarvis-s-core-code`.

So this document is **not a code change and not a code review**. It contains:

- Where input cost usually goes in LLM content and video pipelines, with a
  way to check each point once the code is available (section 1).
- Concrete measures for cost (section 2), learning (section 3) and
  references (section 4). Each measure comes with a quality guard, so that a
  saving that hurts quality gets caught and rolled back.
- A list of tools and external databases (section 5). For the Python
  packages, the name, licence and date of the latest release were checked on
  PyPI (and GitHub for Remotion and LLMLingua) while this was written. **Vendor prices were not checked**: the sandbox could reach only
  GitHub and PyPI, not vendor websites. Where this document mentions
  discounts, check the current price list before relying on them.
- A priority order (section 6) and open questions for Tom (section 7).

**The first step (P0-1) is to give the Dev agent read access to the /Content
and /Video code, plus a sample of recent run logs with token counts.** With
those, sections 1 and 2 can become real fixes with tests.

### Effort scale

| Size | Meaning |
|------|---------|
| **S** | One function or config change, one or two focused tests, low risk. |
| **M** | One module, a handful of tests or a fixture, moderate risk. |
| **L** | Several modules or a new component, integration tests, needs a design note. |

---

## 1. Where input cost usually goes (check each point in the code)

"Input" here means everything sent to a model on each call: system prompt,
brand guide, references, history, tool definitions, images and video frames.
In content and video pipelines, input tokens usually cost far more in total
than output tokens, because the same large context is sent again on every
step and every retry.

| # | Likely cost driver | How to confirm |
|---|--------------------|----------------|
| D1 | **The same static text is sent uncached on every call.** System prompt, brand or tone guide, format rules and tool schemas make up most of each request but never change. | Log input tokens per call and diff the prompts between calls. If most of the prefix is the same, caching will pay off. |
| D2 | **The static part is not at the start of the prompt.** Caching only matches an identical *prefix*. A timestamp, task ID or user message placed before the brand guide breaks the cache on every call. | Check how the prompt is assembled. Look for `datetime.now()`, IDs or user text near the top. |
| D3 | **Whole source documents are pasted in** where a few relevant passages would do. | Compare the size of the references sent with the parts the output actually uses. |
| D4 | **Full conversation or revision history is sent again** on every step. | Check whether token count per call grows with each step of a task. |
| D5 | **The most expensive model does every step**, including classification, metadata, titles, hashtags and checks. | List the model used for each step. |
| D6 | **Images and video frames are sent at full resolution, or every frame is sent.** Vision input is billed by image size. A one-minute clip at even 1 frame per second is 60 images. | Log the image count and size per call. Check how frames are picked. |
| D7 | **A small edit triggers a full regeneration**, such as a whole script or a full render for one changed scene. | Check whether the pipeline can regenerate one section or scene on its own. |
| D8 | **Retries resend everything**, and failed outputs (bad JSON, too long) cost a whole extra call. | Count retries per task and their causes. |
| D9 | **The same research is done again** for similar topics: the same web pages, the same facts, the same stock-media searches. | Hash the research inputs and count duplicates across tasks. |
| D10 | **Output is longer than needed**: prose where JSON would do, many variants when only one is used, no `max_tokens` limit. | Compare output length with what ends up published. |

---

## 2. Reduce cost without reducing quality

**Rule for every item below:** first measure the baseline with the quality
evaluation from Q1. Ship a change only if quality holds within a set
tolerance on that evaluation set. Keep each change behind a setting so it
can be turned off if quality drops.

### 2.1 Measure first

| ID | Measure | Size |
|----|---------|------|
| C0 | **Log every model call**: agent (/Content or /Video), task ID, step, model, input tokens, cached input tokens, output tokens, image count, latency, retry count and estimated cost. Without this, no saving can be shown. Langfuse or OpenLIT (section 5.1) do this with little code. | S–M |
| Q1 | **Quality evaluation set.** 30–50 real briefs for each agent, each with a reference output Tom approved and a scoring rubric (accuracy, brand voice, structure, hook, accessibility). Score with an LLM judge, checked by Tom on a sample. Every change in this plan is gated on this score. | M |

### 2.2 Text inputs (both agents)

| ID | Measure | Expected effect | Quality guard | Size |
|----|---------|-----------------|---------------|------|
| C1 | **Prompt caching with a stable prefix.** Assemble prompts in a fixed order: system prompt → brand guide → format rules → tool schemas → static examples, then the dynamic part (lessons, retrieved references, brief). Nothing that changes per call goes into the prefix. | Large saving on D1/D2. Anthropic, OpenAI and Google all offer cached input at a fraction of the normal input price. Check current prices. | None needed: the model sees exactly the same text. | S |
| C2 | **Batch API for anything that is not urgent**, such as content calendars, bulk captions, translations and evaluation runs. | Providers have offered around half price for batch jobs. Check current prices. | Same model and prompt, so the same quality. Results arrive later, so use it only where waiting is fine. | S–M |
| C3 | **Model routing.** A small model handles classification, metadata, titles, tags, format checks and summaries. The large model handles the creative core: angle, script, final copy. Escalate to the large model when a check fails. | Large saving on D5. | Compare per step on Q1. Route a step to the small model only if its score holds. | M |
| C4 | **Retrieve, don't paste.** Split references into chunks once, store them, and send only the top-k passages for each brief (section 4). | Large saving on D3. Also leaves room for *more* sources. | Measure on Q1 that facts and citations stay right. | M |
| C5 | **Structured brief instead of history.** After each step, keep a short structured state (goal, audience, decisions made, open issues) and send that instead of the full history. | Saving on D4. Token count stays flat as tasks get longer. | Check that decisions are not lost: run Q1 on multi-step tasks. | S–M |
| C6 | **Response cache for research.** Cache fetched web pages, API results and summaries, keyed by URL or query plus date. Reuse them across tasks within a set lifetime. | Saving on D9, and faster delivery. | Set a lifetime per source (news: hours, encyclopedias: weeks) so data does not go stale. | S–M |
| C7 | **Valid output on the first try.** Use the provider's structured output or JSON schema mode (or `instructor` / `pydantic-ai`). Set `max_tokens` and ask for exactly the number of variants needed. | Fewer retries (D8) and shorter output (D10). | Validate against the schema. Count retries in C0. | S |
| C8 | **Budget per task.** A token and cost limit per task, with a warning at 80 % and a clear stop at 100 %. | Stops runaway loops. | The run stops with a reason, it does not silently cut quality. | S |
| C9 | **Prompt compression (optional, last).** Tools like LLMLingua shorten long contexts. | Medium saving. | **High risk for brand voice and exact facts.** Use only on background material, never on the brand guide or quotes, and only if Q1 holds. | M |

### 2.3 Video-specific inputs

| ID | Measure | Expected effect | Quality guard | Size |
|----|---------|-----------------|---------------|------|
| V1 | **Approve the script before rendering.** Script → storyboard (text plus thumbnails) → Tom's approval → render. Mistakes are found while they are cheap to fix. | Avoids paying for renders that get thrown away. Usually the biggest saving in video. | Quality goes up: Tom sees the plan before money is spent. | S–M |
| V2 | **Low-cost drafts, high-quality final.** Draft render at low resolution, short preview or still frames. Final render only after approval. | Saving on render and generation costs. | The final render uses the same settings as today. | S |
| V3 | **Scene-level regeneration.** Store each scene (prompt, assets, voice line, timing) on its own, and regenerate or re-render only changed scenes, then join them with FFmpeg. | Saving on D7. Faster revisions. | Check joins between scenes (audio levels, colour) in the final check. | M |
| V4 | **Smart frame sampling for video analysis.** Pick keyframes with scene detection (PySceneDetect) instead of a fixed frame rate. Downscale frames to the smallest size that keeps the needed detail. | Large saving on D6, often fewer images by an order of magnitude. | Compare analysis results on sample clips before and after. | S–M |
| V5 | **Transcribe locally.** Use faster-whisper or WhisperX for transcripts and subtitles instead of paid speech-to-text, and send the *transcript* to the LLM, not audio or frames, wherever text is enough. | Saves speech-to-text cost and vision tokens. | Check word error rate on Norwegian and English samples. Use a large Whisper model for Norwegian. | S–M |
| V6 | **Cache voice-over and assets.** Store generated voice lines, images and music cues, keyed by a hash of text, voice and settings. Reuse them instead of generating again. | Saving on repeated TTS and image generation. | Same input, same output, so no quality change. | S |
| V7 | **Generate small, then upscale.** Where image or video generation is priced by resolution, generate at a lower resolution and upscale (for example Real-ESRGAN). | Medium saving. | **Test on real content first.** Upscaling can smear text and faces, so skip it for those. | M |
| V8 | **Faster delivery: parallel rendering and GPU encoding.** Render scenes in parallel through a job queue. Use hardware encoding (NVENC/QSV) for drafts and a quality preset for the final. | Shorter delivery time, less paid compute time. | The final encode keeps today's quality settings. | M |

---

## 3. Make learning essential

Today it is unknown whether /Content and /Video learn anything between tasks.
The aim is that **every task starts by fetching what has been learned, and
every finished task adds to it**. It should not be an optional extra.

| ID | Measure | Size |
|----|---------|------|
| L1 | **Capture feedback in a structured way.** For each output, store Tom's decision (approved, edited, rejected), the diff between draft and final version, and the reason when given. Later, add publishing results (views, retention, click-through rate, saves) from the platforms' analytics APIs. | M |
| L2 | **Exemplar library ("dynamic few-shot").** Approved outputs are stored with metadata (format, platform, topic, audience, performance). For each new brief, the 3–5 most similar *good* examples are retrieved and put into the prompt. This raises quality and gives more references, at bounded cost (C4). | M |
| L3 | **Lessons file distilled from edits.** On a schedule, a model reads recent diffs and rejections and proposes short rules ("Tom always removes exclamation marks in headlines", "videos under 45 s keep viewers better on Shorts"). **Tom approves each rule** before it is used. Rules are versioned and can be rolled back. | M |
| L4 | **Learning is a required pipeline step.** Every run fetches approved lessons (L3) and similar examples (L2) before it writes. If the memory store cannot be reached, the run is marked "without learning" in the output and the log. It must never quietly carry on as if nothing were wrong. | S |
| L5 | **Learning must be measured.** Track Q1 score, approval rate on first try and number of edits per output over time. If they do not improve, the learning step is not working. | S |
| L6 | **Learning from results.** Link publishing results back to features of the output (hook type, length, format, time of posting). Use this to rank examples in L2 and to propose rules in L3. | M–L |
| L7 | **Fine-tuning only later.** Consider fine-tuning a small model on approved outputs only after L1–L3 have collected enough data. Until then, retrieval and lessons give most of the gain, at lower risk. | L |

**Guards for learning:**

- Rules and examples can carry mistakes forward. Tom's approval (L3) and
  rollback stop this.
- Feedback and examples can contain personal data. Decide how long they are
  kept, and remove them on request.
- Text from analytics, comments and external sources is **data, not
  instructions**. It must never be able to change the agent's rules without
  Tom's approval (prompt injection).

---

## 4. More references and inputs, without higher cost

More sources only help if the model gets the *relevant* parts of them.
Retrieval (C4) makes it possible to have many more sources while sending
fewer tokens.

| ID | Measure | Size |
|----|---------|------|
| R1 | **Reference store.** One store for all sources: Tom's notes, earlier content, brand material, research, transcripts, stock-media metadata. Each chunk has metadata: source, date, licence, reliability and language. | M |
| R2 | **Hybrid search.** Combine keyword search (BM25) with vector search, using reciprocal rank fusion, plus an optional reranker. Exact names and product names are found reliably this way. | M |
| R3 | **More sources per brief, fewer tokens per source.** Fetch for example 30 candidates, rerank, and send the best 5–8 passages with source citations. Coverage goes up and input size stays flat. | S–M |
| R4 | **Source diversity and quality.** Score sources on reliability. Require at least two independent sources for factual claims. Remove near-duplicates (MinHash) so the same press release does not count as five sources. | M |
| R5 | **Required citations.** Every factual claim in /Content output links to its source. /Video scripts keep a source list. This makes checking quick and lowers the risk of errors. | S |
| R6 | **Media references.** For /Video: a searchable library of earlier scenes, b-roll, music and visual style references (thumbnails, colour palette), so the agent reuses approved assets before it generates or buys new ones. | M |
| R7 | **External databases** for facts, statistics and media (section 5.5 and 5.6), behind the cache from C6. | M |

---

## 5. Tools, extensions and external databases

The column **Helps** shows the main gain: **Q** = quality, **C** = cost,
**T** = delivery time. Licences and latest release dates of Python packages
were checked on PyPI when this was written. Non-Python tools (FFmpeg,
the pgvector extension) and the external databases were not checked online.
"Not maintained" means no release for a long time. Check paid services'
prices and terms before adopting them.

### 5.1 Cost tracking, routing and caching

| Tool | What it does | Helps | Licence / note |
|------|--------------|-------|----------------|
| **Langfuse** | Traces, token and cost per call, prompt versions, evaluation scores. Can be self-hosted. | C, Q | MIT (core). Good fit for C0 and Q1. |
| **OpenLIT** | OpenTelemetry-based tracing and cost tracking for LLM and GPU. | C | Apache-2.0 |
| **Arize Phoenix** | Tracing and evaluation, runs locally. | Q, C | Elastic-2.0 (not OSI open source; check the terms). |
| **LiteLLM** | One API in front of many model providers. Routing, fallback, budgets per key and team, response caching. | C, T | MIT. Good fit for C3, C6 and C8. |
| **RedisVL** | Semantic cache and vector search on Redis. | C, T | MIT. Actively maintained. |
| GPTCache | Semantic cache for LLM calls. | C | MIT. **Not maintained** (last release 2024). Use LiteLLM caching or RedisVL instead. |
| **instructor / pydantic-ai** | Structured, validated output with automatic retry on schema errors. | C, Q | MIT. Fits C7. |
| LLMLingua | Prompt compression. | C | MIT. Last release 2024. Only for C9, with caution. |

### 5.2 Quality evaluation

| Tool | What it does | Helps | Licence / note |
|------|--------------|-------|----------------|
| **promptfoo** | Test prompts and models against an evaluation set from YAML. Runs in CI and compares models side by side on cost and quality. | Q, C | MIT. Good fit for Q1 and C3. |
| **Inspect AI** | Evaluation framework from the UK AI Security Institute. | Q | MIT |
| **DeepEval** | Unit-test-style LLM evaluation with ready-made metrics. | Q | Apache-2.0 |
| **Ragas** | Evaluates retrieval quality: did the answer use the right sources? | Q | Apache-2.0. Fits section 4. |

### 5.3 Retrieval and reference store

| Tool | What it does | Helps | Licence / note |
|------|--------------|-------|----------------|
| **pgvector** | Vector search in PostgreSQL. A good choice if Jarvis already uses Postgres. | Q, C | PostgreSQL licence |
| **Qdrant** / **LanceDB** / **Chroma** | Standalone vector databases. LanceDB runs embedded with no server. | Q | Apache-2.0 |
| **bm25s** / **tantivy** | Fast keyword search for hybrid search (R2). | Q | tantivy: MIT |
| **sentence-transformers**, **FlagEmbedding** (BGE models, BGE reranker) | Local embeddings and reranking. No cost per call. | Q, C | sentence-transformers: Apache-2.0. Check the licence of FlagEmbedding and of each model. |
| **model2vec** | Very fast, small embedding models. Useful for dedup and pre-filtering. | C, T | MIT |
| **datasketch** | MinHash for removing near-duplicate sources (R4). | Q, C | MIT |

### 5.4 Reading documents and the web

| Tool | What it does | Helps | Licence / note |
|------|--------------|-------|----------------|
| **Docling** (IBM) | PDF, DOCX and PPTX to structured Markdown, with tables and layout. | Q, C | MIT |
| **Unstructured** | Splits many file formats into elements. | Q | Apache-2.0 |
| **trafilatura** | Extracts the main text from web pages without menus and ads. Far fewer tokens than raw HTML. | C, Q | Apache-2.0 |

### 5.5 Video, audio and images

| Tool | What it does | Helps | Licence / note |
|------|--------------|-------|----------------|
| **FFmpeg** | Cutting, joining, encoding, burning in subtitles, loudness normalisation. The base for V3 and V8. | C, T | LGPL/GPL depending on the build. |
| **PySceneDetect** (`scenedetect`) | Scene detection, used for keyframe sampling (V4). | C | BSD-3-Clause |
| **faster-whisper** / **WhisperX** | Local transcription. WhisperX adds word-level timing for exact subtitles. | C, Q | MIT / BSD-2-Clause. Fits V5 and accessibility. |
| **auto-editor** | Cuts out silence and dead air automatically. | T | Unlicense |
| **MoviePy** | Video editing from Python, for templates. | T | MIT |
| **Remotion** | Video as code (React). Reusable templates for intros, captions and graphics. | T, Q | **Company licence needed** for for-profit organisations with more than 3 employees. Free for individuals and small companies. |
| Piper | Local text-to-speech, with Norwegian voices. | C | **GPL-3.0** from version 1.3. Check that this fits how it is used. Check voice quality against a paid TTS on Q1. |
| Real-ESRGAN | Upscaling (V7). | C | BSD-3-Clause. **Not maintained** (last release 2022). |
| rembg | Background removal. | T | MIT |
| **c2pa-python** | Content Credentials: marks AI-generated content and its origin. | Q | MIT or Apache-2.0. Relevant for transparency about AI content. |

### 5.6 External databases

**General rules for all external sources:** check terms of use and
licensing for every source, and store the licence and attribution together
with each asset. Treat all fetched text as untrusted data (prompt injection).
Cache results (C6). Keep API keys in environment variables or a secrets
manager, never in code.

**Facts and research**

| Source | What it gives | Helps |
|--------|---------------|-------|
| **Wikidata** (SPARQL) and **Wikipedia API** | Structured facts, dates, names and relationships. Free. | Q |
| **OpenAlex**, **Crossref**, **Semantic Scholar**, **arXiv** | Research articles and metadata, for content that needs research to back it up. | Q |
| **GDELT** | Global news events, for trend and current-affairs angles. | Q |
| **SSB API** (Statistics Norway) | Official Norwegian statistics. Free, open licence (NLOD). | Q |
| **Nasjonalbiblioteket API** (nb.no) | Norwegian books, newspapers and images. Check rights for each item. | Q |
| **data.norge.no** | Index of open Norwegian public datasets. | Q |

**Media for /Video**

| Source | What it gives | Note |
|--------|---------------|------|
| **Pexels API**, **Pixabay API** | Free stock photos and video. | Free licence with conditions. Check rules on attribution and resale. |
| **Unsplash API** | Photos. | Free, with API rules on attribution. |
| **Openverse** | Search across Creative Commons media. | Check the CC licence of each item (BY, BY-SA, NC). |
| **Wikimedia Commons** | Images, video and audio under free licences. | Attribution is usually required. |
| **Freesound API** | Sound effects. | CC licences vary per sound. |
| **DigitaltMuseum API** | Images from Norwegian and Swedish museums. | Check rights for each item. |
| **NASA Image and Video Library** | Space and science footage. | Mostly public domain. Logo and other rules apply. |
| **Internet Archive**, **Europeana** | Archive film, images and audio. | Rights vary a lot. Check each item. |

**Learning from results (L1, L6)**

| Source | What it gives |
|--------|---------------|
| **YouTube Data API** and **YouTube Analytics API** | Views, viewer retention and click-through rate for each video. |
| **Meta Graph API** (Instagram and Facebook Insights) | Reach, saves and shares. |
| **TikTok API** | Results for each video (check which access level is available). |
| **Google Search Console API** | Search terms and clicks for web content. |

Analytics data may contain personal data. Follow GDPR, and store only
aggregated numbers where that is enough.

### 5.7 Accessibility (part of the RESONVALE launch standard)

Accessibility is both a quality requirement and a cost saver when it is
automated:

- **Subtitles on all video** (WCAG 1.2.2) generated with WhisperX (V5),
  then checked by a person. The Norwegian regulations on universal design of
  ICT build on WCAG. Check which version and which criteria apply to
  RESONVALE.
- **Audio description or a text alternative** where the image carries
  information that is not spoken (WCAG 1.2.3/1.2.5).
- **Alt text for images** in /Content, generated by a model and checked.
- **Contrast checks** for text on images and in thumbnails (WCAG 1.4.3), plus
  a rule that information is never shown by colour alone.
- **No flashing content** above three flashes per second (WCAG 2.3.1). This
  can be checked automatically on the frames picked in V4.

---

## 6. Priority order

Priority means the order of the work, not dates.

| Priority | Items | Why this order |
|----------|-------|----------------|
| **P0: unblock** | P0-1: give the Dev agent read access to the /Content and /Video code, plus sample run logs. P0-2: C0 call logging (S–M). P0-3: Q1 evaluation set (M). | Without the code, every saving is a guess. Without measurement and an evaluation set, no one can show that quality holds. |
| **P1: savings with no quality risk** | C1 prompt caching (S), C7 structured output (S), C8 budgets (S), V1 script approval before render (S–M), V6 asset cache (S), C2 batch jobs (S–M). | The same model sees the same input, so quality cannot drop, yet these remove most of the waste. |
| **P2: learning as a required step** | L1 feedback (M), L2 example library (M), L4 required learning step (S), L5 measuring learning (S), then L3 lessons file (M). | Builds the base for better quality on every task. |
| **P3: more references** | R1 reference store (M), R2 hybrid search (M), C4 retrieval instead of pasting (M), R3/R5 more sources with citations (S–M), C6 research cache (S–M), R7 first external sources (M). | More and better sources, while input size goes *down*. |
| **P4: savings that need an evaluation gate** | C3 model routing (M), C5 structured brief (S–M), V2 low-cost drafts (S), V3 scene-level regeneration (M), V4 frame sampling (S–M), V5 local transcription (S–M). | Large savings, but each one must pass Q1 before it ships. |
| **P5: delivery time and depth** | V8 parallel rendering (M), R4 source quality (M), R6 media library (M), L6 learning from results (M–L), accessibility automation (5.7). | Faster delivery and the long-term quality loop. |
| **P6: only with good reason** | C9 prompt compression (M), V7 upscaling (M), L7 fine-tuning (L). | Highest risk to quality. Do these only if the data shows a clear gain. |

## 7. Open questions for Tom

1. Where is the /Content and /Video code, and can the Dev agent get read
   access to it?
2. Which model providers and models do /Content and /Video use today, and
   what does a typical task cost? Are there logs with token counts?
3. What does /Video produce: AI-generated video, edited stock footage, slides
   with voice-over, or something else? Which render or generation services
   are used?
4. Do earlier approved outputs exist that can seed the example library (L2)
   and the evaluation set (Q1)?
5. Which platforms are content published on, and can Jarvis get read access
   to their analytics (L1, L6)?
6. Is it fine to send drafts and references to external APIs, or must some
   material stay local (privacy)?
7. Which is more important when they conflict: lowest cost or shortest
   delivery time? This decides how much goes through batch jobs (C2).
