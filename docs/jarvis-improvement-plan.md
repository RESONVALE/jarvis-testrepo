# Jarvis core: improvement proposal plan

Status: **draft proposal, no production code changed.**

## 0. Read this first: what this plan is based on

The task was to investigate Jarvis's core code. **That code is not available to
the Dev agent.** This repository (`RESONVALE/jarvis-testrepo`) contains only the
`greeter` practice package, and the agent's credentials cannot reach any other
RESONVALE repository (`jarvis`, `jarvis-core`, `jarvis-assistant` and similar
names all return "Repository not found").

So this plan is **not a code review**. It is built from:

1. The symptoms Tom described: files in `12. Ideas` and its subfolders, such as
   `12. Ideas\Jarvis_media\test.md` and `Nisje for Vestigial Souls.pdf`, never
   show up in the index.
2. Common failure modes for Python file indexers on Windows. The ones marked
   **(verified)** were reproduced with Python 3.11 in the agent sandbox
   (Linux). See section 1.2.
3. How the Dev agent pipeline behaves as seen from this repo (branch rules,
   the summary format, PR-only merges).

Each indexer hypothesis below includes a quick way to confirm or rule it out
once someone with access opens the code. **Step P0-1 is to give the Dev agent
read access to the Jarvis core repository** (or attach the indexer source), so
that this plan can become a fix with tests.

### Effort scale

Sizes describe scope and risk, not calendar time:

| Size | Meaning |
|------|---------|
| **S** | One function or config change, one or two focused tests, low risk. |
| **M** | One module, a handful of tests or a test fixture, moderate risk. |
| **L** | Several modules or a new component, integration tests, needs a design note. |
| **XL** | Cross-cutting change touching the architecture or data model. Split it before starting. |

---

## 1. Priority one: the document indexer misses `12. Ideas`

### 1.1 Symptom

- Not indexed: `12. Ideas\Jarvis_media\test.md` (plain Markdown in a subfolder).
- Not indexed: `12. Ideas\…\Nisje for Vestigial Souls.pdf` (PDF, spaces in the name).
- Other numbered folders do get indexed, as far as we know. **We need to
  confirm this**, because it decides which hypotheses fit (see 1.3).

Both a plain `.md` file and a PDF are missing. That points to a cause at the
**folder level** (discovery, filters, recursion, permissions, sync state),
not only a missing PDF parser. There may be two separate bugs, one for folders
and one for PDFs, and the plan treats them separately.

### 1.2 Candidate root causes, ranked by how likely they are

| # | Hypothesis | Why it fits | How to confirm in the code | Verified pitfall |
|---|-----------|-------------|----------------------------|------------------|
| H1 | **Folder allowlist or numbered-prefix regex excludes "12."** For example, `^\d\. ` only matches single digits (`1.`–`9.`), or the config lists folders `01`–`11` because `12. Ideas` was created later. | Only one numbered folder fails, and it is the newest and highest-numbered one. | Search for `re.compile`, `\d`, `include`, `folders`, `roots`, `whitelist`/`allowlist` in the indexer and its config. | `re.match(r"^\d\. ", "12. Ideas")` → no match; `^\d+\. ` matches **(verified)** |
| H2 | **A dot in the folder name is read as a file extension.** Code like `os.path.splitext(name)[1]`, `Path(name).suffix` or `"." in name` decides "file or folder" or applies an extension filter to directories. | `"12. Ideas"` contains a dot. If the parent folder is dropped, every subfolder under it goes too. | Search for `splitext`, `.suffix`, `"." in`, `endswith(` used on directory entries. | `os.path.splitext("12. Ideas")` → `('12', '. Ideas')`; `Path("12. Ideas").suffix` → `'. Ideas'` **(verified)** |
| H3 | **No subfolder recursion.** The indexer uses `glob("*.md")`, `glob("**/*.md")` without `recursive=True`, `Path.glob("*")`, `os.listdir`, or a watcher started with `recursive=False`. | `test.md` sits one level down, in `Jarvis_media`. | Search for `glob(`, `listdir`, `scandir`, `rglob`, `recursive=`. | `glob.glob("**/*.md")` without `recursive=True` misses `12. Ideas/Jarvis_media/test.md`; `Path.glob("*.pdf")` misses nested PDFs, `rglob` finds them **(verified)** |
| H4 | **Exclude pattern hits `media`.** Many indexers skip `*media*`, `assets`, `attachments` or `_*` folders, which would match `Jarvis_media`. | Explains the subfolder only, not the PDF in `12. Ideas` itself, unless the PDF is also inside `Jarvis_media`. | Search for `exclude`, `ignore`, `skip`, `.jarvisignore`, `fnmatch`. | n/a |
| H5 | **Errors while walking are swallowed.** `os.walk()` defaults to `onerror=None` and silently skips folders it cannot read (permissions, OneDrive placeholder, path too long). A broad `try/except: pass` around each file does the same. | Nothing in the logs would ever mention the folder. | Search for `os.walk(` without `onerror=`, and for `except Exception: pass` / `except: continue`. | An unreadable `12. Ideas` simply disappears from `os.walk` output, with no exception **(verified)** |
| H6 | **Spaces split or break the path.** For example, `cmd.split()` or `shell=True` with string concatenation when calling `pdftotext`, a CSV or space-separated config value, or unencoded URLs. | Both the folder and the PDF name contain spaces. | Search for `shell=True`, `.split()` on paths, `os.system`, f-strings building commands. | `"12. Ideas".split()` → `['12.', 'Ideas']` **(verified)** |
| H7 | **Windows path handling.** Backslashes in JSON/TOML config (`"C:\Users\…\12. Ideas"` is invalid JSON: `\U`/`\J` escapes); a path containing `\` is treated as one name when it runs under Linux, WSL or Docker; or a Docker volume mount covers only some folders. | The paths Tom gave use `\`. | Check where the config root is defined and where Jarvis runs (native Windows, WSL or a container). Check the volume mounts. | Unescaped `\J` → `JSONDecodeError: Invalid \escape`; on POSIX, `PurePosixPath(r"12. Ideas\Jarvis_media").parts` is a single part **(verified)** |
| H8 | **Incremental re-index skips "old" files.** The change check compares `mtime > last_indexed_at`. Copying, unzipping or syncing files keeps their original mtime, so files that are new to the index look old. | Files that were moved or copied into `12. Ideas` would never be picked up. | Look at the "changed since" logic and the stored state (`last_run`, `mtime`, hash table). | `shutil.copy2` (like Explorer copy) keeps the source mtime **(verified)** |
| H9 | **Cloud-sync placeholders.** OneDrive or Google Drive "files on demand" exist only as stubs until opened. Readers fail on them or skip them, and some walkers skip reparse points entirely. | Ideas and media folders are often synced and set to "online only". | In Explorer, check the folder's status icon (cloud vs. green tick). Look for attribute or `is_symlink`/reparse checks. | n/a (Windows only) |
| H10 | **The PDF extractor is missing or fails silently.** `.pdf` is not in the allowed extensions, the extractor returns `""` for scanned or image-only PDFs, or a size limit drops large PDFs. Empty text gives zero chunks, so the document "doesn't exist". | Covers the PDF but not `test.md`, so at least one other cause must exist too. | Search for `ALLOWED_EXT`, `SUPPORTED`, `.pdf`, `pypdf`/`PyPDF2`/`pdfminer`/`fitz`, `max_size`. | n/a |
| H11 | **Document IDs collide.** The ID is built from the file name or stem only, so `test.md` overwrites (or is overwritten by) another `test.md` elsewhere. | Generic names like `test.md` are the most likely to collide. | Look at how the doc ID or primary key is built. | n/a |
| H12 | **Windows MAX_PATH (260 characters) or Unicode normalization.** Deep folders under a long user or OneDrive root go over 260 characters. Names with `æøå` may be stored as NFD on one side and NFC on the other, so lookups miss. | Less likely for these exact names, but common in the same vault. | Measure full path lengths. Check for `unicodedata.normalize`. | `NFC("Idéer") != NFD("Idéer")` **(verified)** |

### 1.3 Diagnostic steps, before writing any fix (P0, size S)

Do these in order. Each one rules hypotheses in or out.

1. **Get the facts about the environment.** Where does Jarvis run (native
   Windows, WSL or Docker)? What exact index root is configured? Is the vault
   synced by OneDrive or another service? → H7, H9.
2. **Compare the disk with the index.** List every file under the vault root
   recursively (`Get-ChildItem -Recurse -File` or `os.walk` with an `onerror`
   that prints). Compare it with the document paths stored in the index, and
   group the missing files by top-level folder and by extension.
   - All of `12.*` missing, everything else present → H1 or H2.
   - Only nested files missing, in every folder → H3.
   - Only `*media*` folders missing → H4.
   - Only PDFs missing → H10.
   - Scattered, recently copied files missing → H8.
3. **Run the indexer once with debug logging on `12. Ideas` alone**, if it
   supports a path argument. Every file should end up in one of these states:
   discovered, skipped (with reason), failed (with error), or indexed (with
   chunk count). If the logs have no line for `12. Ideas` at all, the folder
   was never discovered → H1, H2, H5 or H7.
4. **Run a text extraction on `Nisje for Vestigial Souls.pdf` by hand**
   (for example `pypdf` or `pdftotext`). Empty output means the PDF is scanned
   or image-only → OCR is needed (H10).
5. **Try a rename.** Copy `12. Ideas` to `12 Ideas` (no dot) and to `Ideas`
   in a scratch vault and index those. If they work, the cause is H1 or H2.

### 1.4 Proposed fixes

| ID | Fix | Size | Covers |
|----|-----|------|--------|
| IDX-1 | **Discover files with one recursive walker.** Use `os.walk(root, onerror=log_and_continue, followlinks=False)` or `Path.rglob("*")`, and filter files only, never directories, by extension using a case-insensitive allowlist (`.md`, `.txt`, `.pdf`, …). Never apply `splitext` or `suffix` to directories. | M | H2, H3, H5 |
| IDX-2 | **Make folder include and exclude rules explicit and testable.** Default to "everything under the root". Exclusions are glob patterns matched against the *relative path* (`.git/**`, `node_modules/**`), with no broad name patterns like `*media*`. If numbered folders matter, use `^\d+\.\s`. Log the effective rules at startup. | S | H1, H4 |
| IDX-3 | **Handle paths with `pathlib` from end to end.** Store the root as a `Path` and store document paths as POSIX-style paths relative to the root, normalized to NFC. Never split, concatenate or quote paths by hand. Call subprocesses with an argument list, never `shell=True`. In config files, accept forward slashes or raw strings, and fail at startup with a clear message if the root does not exist. | S–M | H6, H7, H12 |
| IDX-4 | **Make PDF support solid.** Extract text with `pypdf` (pure Python) and keep page numbers for citations. If a PDF yields almost no text, mark it `needs_ocr` and optionally run OCR (Tesseract or `ocrmypdf`) behind a setting. Encrypted, corrupt and oversized PDFs get an explicit `skipped` status with a reason, never a silent drop. | M (L with OCR) | H10 |
| IDX-5 | **Use stable document IDs.** Build the ID from the relative path, normalized (for example `sha1(relpath_nfc)`). Store a content hash separately for change detection. | S | H11 |
| IDX-6 | **Re-index triggers.** (a) On change, compare *content hash plus size*, not just mtime against the last run. (b) Run a full reconciliation pass on startup and on a schedule: index paths that are on disk but not in the index, delete paths that are in the index but not on disk, and re-index files whose hash changed. (c) Optionally add a live watcher (`watchdog`, `recursive=True`) with debounce, handling create, modify, move/rename and delete. (d) Add a manual "re-index this folder" command or button, with a dry-run mode. | M (watcher: +M) | H8 |
| IDX-7 | **Cloud placeholders and long paths.** Detect placeholders (Windows file attributes) and report them as `skipped: offline placeholder`, or hydrate them if a setting allows. Use `\\?\` long-path prefixes, or require the long-paths registry setting, and log any path over 260 characters. | S–M | H9, H12 |
| IDX-8 | **Coverage report.** After each run, emit counts per top-level folder and extension (discovered, indexed, skipped by reason, failed), plus a list of files that are on disk but not in the index. This is what would have made this bug obvious. | S | All |

### 1.5 Tests for the indexer fix (must ship with IDX-1 to IDX-8)

Build a temporary vault fixture (`tmp_path`) that mirrors the real structure:

```
vault/
  03. Notes/a.md
  12. Ideas/
    idea.md
    Nisje for Vestigial Souls.pdf        ← small generated PDF with known text
    Jarvis_media/test.md
    Jarvis_media/deeper/level3.md
  Ærlige idéer/nfd-navn.md               ← name stored as NFD
  .git/ignored.md                        ← must be excluded
  scanned.pdf                            ← image-only, expect needs_ocr
  broken.pdf                             ← corrupt, expect skipped with reason
```

Test cases:

1. Every expected file is discovered, including names with dots, spaces,
   Norwegian characters, and files three levels deep.
2. `.git/**` is excluded; `Jarvis_media` is **not**.
3. The text of `Nisje for Vestigial Souls.pdf` is searchable, and the result
   cites the right page.
4. Scanned and corrupt PDFs get explicit statuses and do not stop the run.
5. An unreadable folder is logged as an error, and its sibling folders are
   still indexed.
6. Re-index: add a file → indexed; edit → updated; delete → removed;
   rename → same content, new path, no duplicate; **copy in a file with an old
   mtime → indexed** (H8 regression test).
7. Two `test.md` files in different folders both stay in the index (H11).
8. Config with a Windows-style root (`C:\…\12. Ideas`) is parsed correctly or
   rejected with a clear message.
9. Run the suite on **Windows and Linux** in CI. Several of these bugs only
   show up on Windows.

---

## 2. Other improvements

These cannot be confirmed without the code. Each item says what to check
first.

### 2.1 Memory and search quality

| ID | Proposal | Size |
|----|----------|------|
| MEM-1 | **Golden evaluation set.** 30–50 real questions with the documents that should answer them (include `12. Ideas` content). Measure recall@k and MRR on every change to chunking, embeddings or ranking. Without this, search changes are guesswork. | M |
| MEM-2 | **Structure-aware chunking.** Split Markdown on headings and PDFs on pages and paragraphs, with overlap. Store the title, heading path, folder and page as metadata on every chunk. | M |
| MEM-3 | **Hybrid retrieval.** Combine BM25 keyword search with vector search (for example reciprocal rank fusion). This helps with exact names like "Vestigial Souls" that embeddings often blur. Optionally add a reranker. | M–L |
| MEM-4 | **Metadata filters.** Allow "search only in 12. Ideas" or "only PDFs", and boost recently changed items. | S–M |
| MEM-5 | **Source citations in every answer** (path and page or heading), so Tom can check where an answer came from. | S |
| MEM-6 | **Separate memory types.** Keep long-term facts about Tom, conversation history and indexed documents apart, each with its own retention and deletion rules. Allow "forget this", and remove deleted files from memory (ties in with IDX-6b). | L |
| MEM-7 | **Re-embed when the model changes.** Store the embedding model name and version with each vector, and re-embed in the background when it changes, instead of mixing vector spaces. | S–M |

### 2.2 Agent orchestration

| ID | Proposal | Size |
|----|----------|------|
| ORC-1 | **Typed task contracts.** Every agent (Dev, research, …) gets an input schema and an output schema. The Dev agent's `<sammendrag>` JSON should be validated against a JSON Schema, and a malformed summary should be rejected with a clear error, not parsed by hand. | M |
| ORC-2 | **An explicit state machine for each task** (queued → running → awaiting approval → done or failed or cancelled), persisted so tasks survive a restart. | L |
| ORC-3 | **Timeouts, step and token budgets, and cancellation for each agent run.** A stuck agent should fail with a reason, not hang. | M |
| ORC-4 | **Safe retries.** Retry with backoff only on transient errors (network, rate limits), and make side effects idempotent, for example by keying each task on a stable branch name. | M |
| ORC-5 | **Treat context as untrusted.** Tool results, repository text and *indexed documents* are data, not instructions. This matters more once `12. Ideas` is indexed, because any note could contain text that looks like an instruction. Keep system instructions separate from retrieved content, and keep tool permissions minimal for each agent. | M |

### 2.3 Approval queue

| ID | Proposal | Size |
|----|----------|------|
| APR-1 | **A persistent queue** (SQLite or similar) instead of in-memory, so pending approvals survive a restart. | M |
| APR-2 | **Show what will happen.** Each request includes a diff or preview, risk level, the files affected and the agent's summary, so Tom approves the actual change, not a description of it. | M |
| APR-3 | **Exactly-once execution.** An approval token is bound to one specific action and its parameter hash. It is used once, expires after a set lifetime, and cannot be replayed or double-clicked into running twice. | M |
| APR-4 | **Policy tiers.** Read-only actions are auto-approved. Writes to a working branch are approved per batch. Anything touching `main`, releases, deletions, secrets or external messages always needs explicit approval. Server-side branch protection on `main` stays the final safeguard. | M |
| APR-5 | **Audit log.** Record who approved what, when, with which parameters, and the outcome. Append-only. | S |

### 2.4 Reliability

| ID | Proposal | Size |
|----|----------|------|
| REL-1 | **Health checks** for the indexer, vector store, LLM provider and approval queue, plus a `jarvis status` command that shows the last index run and coverage (IDX-8). | S–M |
| REL-2 | **Graceful degradation.** If the vector store or LLM is down, report this clearly and fall back where possible, for example to keyword search only. | M |
| REL-3 | **Background job runner** for indexing and re-embedding, with resume after a crash (checkpoint by file), so a crash at file 900 of 1,000 does not restart from zero. | M |
| REL-4 | **Back up the index and memory stores, and test a restore.** | S |
| REL-5 | **Pinned dependencies** (lock file) and reproducible environments, on Windows and Linux. | S |

### 2.5 Error handling

| ID | Proposal | Size |
|----|----------|------|
| ERR-1 | **Remove silent failures.** Find every bare `except:`, `except Exception: pass` and `os.walk` call without `onerror`. Either handle the specific exception or log and re-raise. (Ruff rules `BLE`, `E722`, `S110` and `SIM105` can find these.) | S–M |
| ERR-2 | **A small error taxonomy.** User error, transient, permanent and bug, each with a defined retry and reporting behavior. | M |
| ERR-3 | **Clear, accessible error messages for users.** Say what failed, which file or folder, and what to do. Never show a stack trace to the user. Do not convey status by colour alone in the UI. | S–M |
| ERR-4 | **Validate input at the boundaries.** Config at startup (the root exists, patterns are valid, sizes are positive), plus user commands and tool arguments. No path may resolve outside the vault root (block `..` and absolute-path traversal). | S–M |

### 2.6 Logging and observability

| ID | Proposal | Size |
|----|----------|------|
| LOG-1 | **Structured (JSON) logs** with a correlation ID for each task or run, carried across agents and tools. | M |
| LOG-2 | **Redact secrets.** Use a logging filter that masks tokens, keys and passwords, and never logs whole prompts or documents at INFO level. | S |
| LOG-3 | **One log line per file, per index run,** with the outcome and reason (this feeds the IDX-8 coverage report). | S |
| LOG-4 | **Basic metrics:** index duration, documents per status, search latency, LLM errors, approval wait time. | M |

### 2.7 Tests and CI

| ID | Proposal | Size |
|----|----------|------|
| TST-1 | **CI on every PR:** `ruff check`, `ruff format --check` and the test suite, on a Windows plus Linux matrix. This repo has a Ruff config but no CI workflow yet, so it is a good place to prove the setup. | S |
| TST-2 | **Indexer fixture suite** (section 1.5). | M |
| TST-3 | **Contract tests** for each agent's input and output schema, plus a fake LLM for deterministic orchestration tests. | M |
| TST-4 | **Search regression tests** that run the MEM-1 golden set and fail when quality drops past a set threshold. | M |
| TST-5 | **Approval-queue tests:** expiry, replay, double approval, restart while pending. | S–M |

### 2.8 Security

| ID | Proposal | Size |
|----|----------|------|
| SEC-1 | **Scan for secrets** in the code and git history (`gitleaks` or `trufflehog`), plus a pre-commit hook. Keep secrets only in environment variables or the OS keychain. Rotate anything that is found. | S |
| SEC-2 | **Least-privilege tokens.** The Dev agent's GitHub token should be fine-grained, limited to the repos it needs, with no admin or delete rights. Branch protection on `main` (PR plus review required, no force-push) is enforced on the server. | S |
| SEC-3 | **Defend against prompt injection** (see ORC-5). Mark retrieved content as untrusted, never run tool calls that come from document text, and add red-team test documents to the indexer fixture. | M |
| SEC-4 | **Contain file paths and subprocesses.** No `shell=True`, all paths resolved and checked against the vault root, symlinks not followed out of the root. | S |
| SEC-5 | **Dependency scanning** (`pip-audit`, Dependabot) and pinned versions. Parse PDFs with size and time limits, because PDFs are untrusted input. | S |
| SEC-6 | **Privacy.** Decide what may be sent to external LLM or embedding APIs, and allow folders to be excluded from cloud processing, since personal notes in `12. Ideas` are sensitive. | M |

---

## 3. Prioritized roadmap

Priority means order of work, not dates.

| Priority | Items | Why this order |
|----------|-------|----------------|
| **P0: unblock** | P0-1: give the Dev agent read access to the Jarvis core repo (or attach the source). P0-2: run the diagnostic steps in 1.3 (S). | Without the code, every root cause is a hypothesis. The diagnostics narrow 12 hypotheses down to one or two. |
| **P1: fix indexing** | IDX-8 coverage report (S), IDX-1 recursive walker (M), IDX-2 include/exclude rules (S), IDX-3 path handling (S–M), IDX-5 stable IDs (S), TST-2 fixture suite (M), TST-1 CI with Windows (S). | Fixes Tom's actual problem, with a regression suite so it cannot quietly come back. |
| **P2: complete coverage** | IDX-4 PDF support (M, OCR L), IDX-6 re-index triggers and reconciliation (M, +M for the watcher), IDX-7 placeholders and long paths (S–M), ERR-1 remove silent failures (S–M), LOG-3 per-file outcome logging (S). | Makes sure new, copied, moved and scanned files keep arriving in the index. |
| **P3: safety baseline** | SEC-1 secret scan (S), SEC-2 token scope and branch protection (S), ORC-5/SEC-3 untrusted-context handling (M), APR-3 exactly-once approvals (M), APR-5 audit log (S), LOG-2 redaction (S), ERR-4 input validation (S–M). | Indexing more personal content raises both the prompt-injection risk and the privacy stakes. |
| **P4: search quality** | MEM-1 golden set (M) first, then MEM-2 chunking (M), MEM-3 hybrid retrieval (M–L), MEM-5 citations (S), MEM-4 filters (S–M), MEM-7 versioned embeddings (S–M), TST-4 (M). | Measure first, then tune. |
| **P5: orchestration and reliability** | ORC-1 typed contracts (M), ORC-3 budgets and timeouts (M), ORC-4 safe retries (M), APR-1/APR-2/APR-4 queue upgrades (M each), REL-1 to REL-5, LOG-1, LOG-4, ERR-2, ERR-3, TST-3, TST-5. | Strengthens Jarvis's day-to-day running once the core data path is right. |
| **P6: larger redesigns** | ORC-2 persisted task state machine (L), MEM-6 memory separation (L), SEC-6 privacy controls (M). | Valuable, but each needs its own design note and should be split into smaller pieces. |

## 4. Open questions for Tom

1. Where is the Jarvis core code, and can the Dev agent get read access?
2. Where does Jarvis run: native Windows, WSL or Docker? What is the exact
   configured index root?
3. Is the vault synced with OneDrive or something else, and is `12. Ideas`
   set to "online only"?
4. Are other numbered folders (`10.`, `11.`) indexed correctly? Are nested
   files in other folders indexed?
5. Is `Nisje for Vestigial Souls.pdf` a text PDF or a scan?
6. Is there a reason to exclude media folders (large binaries), or should
   `Jarvis_media` be fully indexed?
