# AI Blog Publisher

An attributed BlogBoard derivative with private drafts, explicit reviewed publication, and a static article reader.

**Status: tested reference implementation.** Offline workflows and desktop/mobile browser checks pass. Live Groq, news-search and R2 integrations have not been verified with real credentials. This is not a production certification, multi-user CMS, factual-accuracy guarantee or uptime commitment.

## Source and Category

- Primary category: Generative and Agentic AI; portfolio placement: Responsible automation.
- Discovered through [AI Project Gallery](https://github.com/KalyanM45/AI-Project-Gallery).
- Adapted from [Hema Kalyan Murapaka's BlogBoard](https://github.com/KalyanM45/Multi-Agentic-Blog-Generation), revision `8b743e21ac0e940dc8bd159f5d94a8f5eb17c630`.
- The original MIT [LICENSE](LICENSE) is preserved. This repository retains upstream history; the workflow and reader originate upstream, not as original work claimed by Sushant Nemade.
- [Catalog](https://github.com/Sushant-Nemade/ai-project-gallery) | [Release evidence](docs/RELEASE_STATUS.md) | [Operations](docs/OPERATIONS.md)

## Quick Start

Requires Python 3.13, uv, Node.js 22 or newer, and npm. Run from the repository root; commands work in PowerShell as well as a Unix shell.

```text
git clone https://github.com/Sushant-Nemade/ai-blog-publisher.git
cd ai-blog-publisher
uv sync --frozen
npm ci --ignore-scripts
npm run build
uv run --frozen python -m blogboard.run --help
uv run --frozen python -m blogboard.run --dry-run
uv run --frozen python -m blogboard.run --ainews --dry-run
```

Help and dry-run need no keys, make no network calls and write no output files. Installing dependencies and security audits do use the network.

## Review and Publish a Fixture

```text
uv run --frozen python -m blogboard.run --fixture
uv run --frozen python -m blogboard.run --draft drafts/<returned-digest>.json
uv run --frozen python -m blogboard.run --draft drafts/<returned-digest>.json --approve <inspected-digest>
uv run --frozen python -m blogboard.run --verify-site
uv run --frozen python -m http.server 8000 --bind 127.0.0.1 --directory blogboard/web
```

Open http://127.0.0.1:8000. The supplied article is explicitly labeled a synthetic fixture, not live AI output. Inspect the complete draft before approving it. The digest covers content and metadata; changing either invalidates previous approval.

## Configured AI Generation

Create a private `.env` locally using `.env.example`. Set `llm__api_key` through your local editor or secret manager, never through chat or a commit. Groq account terms, quotas and costs apply; no paid service is activated by this repository.

```text
uv run --frozen python -m blogboard.run --domain ml --topic "Reliable publishing pipelines"
uv run --frozen python -m blogboard.run --ainews --topic "AI research releases"
```

Live tutorial generation needs Groq. News research additionally needs at least one configured Tavily or Guardian account. These commands save a private draft, not a published article. Follow the same review and approval steps above. News citations and generated technical claims require human verification.

Local history is the default. Optional `STORAGE_BACKEND=r2` uses explicitly configured R2 history; publication remains the reviewed local static-site workflow. Cloud publication transactions, multi-user editing and scheduled AI generation are not implemented.

## Architecture and Improvements

```text
CLI -> LangGraph tutorial/news track -> bounded model calls
    -> strict Pydantic editorial review -> private JSON draft
    -> human inspection + matching digest -> single-writer local publication
    -> validated article index -> sanitized static reader -> gated Pages artifact
```

- Malformed review JSON, missing approval and exhausted revisions fail closed.
- Immutable content-addressed articles and atomic individual file replacement support idempotent retries. A failed index write can leave an unindexed article; multi-file writes are not falsely described as transactions.
- Missing, corrupt and inaccessible indexes are distinct outcomes; failures do not silently erase previous content.
- Provider timeout, retry, token and research-step limits bound execution. Diagnostics do not print provider exceptions or credentials.
- Local content URLs work under the repository Pages subpath. Metadata is validated, interpolated strings are escaped, Markdown is sanitized, and failures offer retry.
- Pinned dependencies, Python/browser tests, security screening and serialized Pages delivery provide inspectable release evidence.

## Verification

```text
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen pip-audit --progress-spinner off
npm test
npm audit
uv run --frozen python -m scripts.prepare_demo
npx playwright install chromium
npm run test:e2e
```

Browser tests use an isolated synthetic site under `build/demo`, cover desktop/mobile viewports, and do not need model keys. Core graph integration tests mock providers and prove routing/storage behavior, not provider availability. CI never generates or approves real articles. Pages deploys only reviewed committed content after CI succeeds.