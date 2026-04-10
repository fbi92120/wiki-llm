# Wiki LLM

A human-piloted LLM tool that maintains a persistent Markdown knowledge base from source files. Unlike traditional RAG systems that rediscover knowledge from scratch on every query, Wiki LLM compiles once, maintains over time, and surfaces cross-cutting connections the user would not have formulated alone.

This is **not** an autonomous agent. Every operation is triggered by a human, supervised, and stops after returning control. Agentic architecture is explicitly deferred to V2-9. See [SPECS.md](SPECS.md) for the full architecture.

## How it works

Concept inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Source files (YouTube transcript summaries in `-reduit.md` format) are ingested into a structured wiki. Each ingestion creates or updates source pages, concept pages, an index, a changelog, and a contradiction tracker. The wiki is designed to be read in [Obsidian](https://obsidian.md/) for graph navigation and clickable links.

## Prerequisites

- Python 3.9+
- git
- pytest (tests only)

## Installation

```bash
git clone <repo-url> && cd wiki-llm
pip install pytest  # only needed to run tests
```

No runtime dependencies beyond the Python standard library.

## Usage

```bash
python3 wiki_ingest.py <path-to-fiche-reduit.md>
```

| Option | Description |
|---|---|
| `--wiki-root PATH` | Wiki root directory (default: `./wiki/`) |
| `--source-dir PATH` | Raw sources directory for R6 integrity check |
| `--question TEXT` | Override the auto-generated cross-cutting question |
| `--no-commit` | Skip the git commit step |
| `--no-validate` | Skip post-ingestion validation |

### Example

```bash
python3 wiki_ingest.py wiki-test/2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md
```

### Running tests

```bash
python3 -m pytest tests/ -v
```

## Project structure

```
wiki-llm/
    wiki_ingest.py          # CLI entry point (Workflow A orchestrator)
    SPECS.md                # Full specifications
    CLAUDE.md               # Project constitution and rules
    src/
        reader.py           # Reads -reduit.md source files
        source_writer.py    # Generates wiki/sources/ pages
        concept_writer.py   # Creates/updates wiki/concepts/ pages
        index_manager.py    # Maintains wiki/index.md
        log_manager.py      # Appends to wiki/log.md
        contradiction_manager.py  # Tracks contradictions between sources
        validator.py        # Post-ingestion rule checker
    wiki/
        index.md            # Page catalog (replaces vector RAG)
        log.md              # Chronological event journal
        contradictions.md   # Detected contradictions
        sources/            # One page per ingested source
        concepts/           # One page per cross-cutting concept
        syntheses/          # User-requested synthesis pages
        a-traiter/          # Insufficient sources pending review
    tests/
        test_contract.py    # 9 contract tests (SPECS.md Bloc 5)
        test_smoke.py       # End-to-end Workflow A test
    wiki-test/              # Test fixtures (-reduit.md files)
```

## Architecture

See [SPECS.md](SPECS.md) for the complete specification, including the constitution (Bloc 0), architecture (Bloc 2), system prompt (Bloc 3), edge cases (Bloc 4), and test strategy (Bloc 5).

## License

Not specified yet.
