---
name: llm-wiki
description: Build and maintain LLM-powered knowledge bases with knowledge graph support. Ingest sources, query wiki, maintain index. Works with Obsidian.
tags: [knowledge-base, wiki, obsidian, research, knowledge-graph]
---

# LLM Wiki

## What this skill does

Helps you build a persistent, compounding knowledge base using LLMs, with automatic knowledge graph generation and graph-based querying.

**Key difference from RAG**: Knowledge is compiled once into a structured wiki, then kept current - not re-derived on every query.

**Knowledge graph**: Automatically builds a graph.json from your wiki's [[wikilinks]], supporting path finding, community detection, hub node analysis, and more.

## Prerequisites

- Wiki directory (set via `LLM_WIKI_PATH` env var, defaults to `~/wiki`)
- Obsidian (optional, for viewing)
- Python 3.10+ (for graph scripts)

## Quick Start

### Initialize a new wiki
```bash
wiki-init ~/my-wiki
```

### Ingest a source
Tell Hermes: "Ingest [file/url] into the wiki"

### Build the knowledge graph
```bash
wiki-graph.py --wiki-path ~/my-wiki --report
```

### Query the graph
```bash
wiki-query.py neighbors "Concept Name"
wiki-query.py path "Node A" "Node B"
wiki-query.py community "Concept Name"
wiki-query.py hubs
wiki-query.py search "keyword"
```

### Health check
```bash
wiki-lint
```

## Directory Structure

When a wiki is initialized, it creates:

```
wiki/
├── HERMES.md          # Schema - tells LLM how to work with this wiki
├── index.md           # Content catalog
├── log.md             # Timeline log
├── graph.json         # Knowledge graph (auto-generated)
├── GRAPH_REPORT.md    # Graph analysis report (auto-generated)
├── raw/               # Source documents (immutable)
│   ├── articles/
│   ├── papers/
│   ├── images/
│   └── other/
├── sources/           # Source summaries (one per raw doc)
├── entities/          # Entity pages (people, companies, projects)
├── concepts/          # Concept pages (topics, technologies, themes)
├── analysis/          # Analysis, comparisons, synthesis
├── output/            # Generated outputs (slides, charts)
└── .cache/            # SHA256 file hashes for incremental updates
    └── graph_hash.json
```

## Operations

### Ingest

When user says: "Ingest [source] into the wiki"

1. **Check cache**: Compute SHA256 of source file. If unchanged and wiki page exists, skip (log as "skipped (unchanged)")
2. **Save raw source** (if URL, download to `raw/`)
3. **Read the source** and extract key information
4. **Create source summary** in `sources/{source-name}.md`
5. **Update/create entity pages** in `entities/`
6. **Update/create concept pages** in `concepts/`
7. **Annotate relations** with confidence (see Confidence Annotations below)
8. **Update index.md** with new entries
9. **Append to log.md** with timestamp

A single source typically touches 5-15 wiki pages.

### Query

When user asks about wiki content:

1. **Read HERMES.md** to understand the wiki context
2. **Check for GRAPH_REPORT.md** - if exists, read it first for hub nodes and community structure
3. **Read index.md** to find relevant pages
4. **Read relevant pages** in detail
5. **Synthesize answer** with citations ([[Page Name]] format)
6. **Optionally use graph queries** for relationship analysis:
   - "What connects X and Y?" → `wiki-query.py path X Y`
   - "What is X related to?" → `wiki-query.py neighbors X`
7. **Optionally file answer back** into wiki if valuable

### Build Graph

When user says: "Build the wiki graph" or "Update the graph"

1. **Run** `wiki-graph.py --wiki-path <path> --report`
2. This scans all wiki pages, builds graph.json, and generates GRAPH_REPORT.md
3. If run again without changes, it skips (SHA256 cache)

### Lint

When user says: "Lint the wiki" or "Check wiki health"

1. **Run** `wiki-lint` (bash script)
2. Checks:
   - Orphan pages (no inbound links)
   - Missing index entries
   - Stale pages (not updated in 30+ days)
   - Confidence annotations (inferred/uncertain counts)
   - Potential duplicate pages (similar names, >=80% match)
   - Knowledge graph status
3. Report findings and suggest fixes

## Confidence Annotations

Relations between wiki pages can be annotated with confidence levels:

| Annotation | Meaning | Example |
|---|---|---|
| (none) | EXTRACTED - directly found in source | `[[Transformer]]` |
| `(inferred)` | INFERRED - LLM deduced this connection | `[[BERT]] (inferred)` |
| `(uncertain)` | AMBIGUOUS - needs verification | `[[Self-Attention]] (uncertain)` |

> ⚠️ **CRITICAL**: wiki-graph.py's regex ONLY matches `(inferred)` or `(uncertain)` immediately after `]]`. Do NOT write `(inferred, some description)` — the description part breaks the regex and the edge will be silently treated as EXTRACTED. If you want to add context, put it AFTER the annotation: `[[BERT]] (inferred) — shares architecture with Transformer`.

**When to use:**
- EXTRACTED (default): The source explicitly mentions the relationship
- INFERRED: The LLM recognizes a conceptual link not explicitly stated
- UNCERTAIN: The connection is speculative or tenuous

**Benefits:**
- The knowledge graph tracks confidence per edge
- GRAPH_REPORT.md shows confidence breakdown percentages
- Lint reports pages with many inferred/uncertain relations
- Users can prioritize verification of low-confidence connections

## Knowledge Graph

### How it works

The graph is built from your wiki's [[wikilinks]] and YAML frontmatter:

1. **Scan** all .md files in sources/, entities/, concepts/, analysis/
2. **Parse** frontmatter for metadata (type, created, updated, tags)
3. **Extract** [[wikilinks]] with confidence annotations
4. **Build** graph.json with nodes, edges, communities, and hub nodes
5. **Detect** communities via connected components (split large ones)
6. **Generate** GRAPH_REPORT.md with analysis

**No external dependencies** - uses only Python standard library.

### Graph Query Modes

```bash
# Find shortest path between two concepts
wiki-query.py path "GPT" "BERT"

# List all connections of a node (grouped by confidence)
wiki-query.py neighbors "Transformer"

# Show all members of a node's community
wiki-query.py community "Self-Attention"

# Show top 10 hub nodes (most connected)
wiki-query.py hubs

# Search for nodes by keyword
wiki-query.py search "attention"
```

### GRAPH_REPORT.md Sections

1. **Overview**: Node/edge/community counts, confidence breakdown
2. **Hub Nodes**: Top 10 most-connected pages
3. **Communities**: Auto-detected clusters with members
4. **Unexpected Connections**: Cross-community edges (interesting bridges)
5. **Orphan Nodes**: Pages with no connections
6. **Suggested Questions**: Auto-generated questions based on graph structure
7. **Stale Pages**: Pages not updated in 30+ days

## Incremental Updates

The system uses SHA256 file hashing to avoid redundant processing:

- **graph.json**: Stores file hashes in `.cache/graph_hash.json`. Re-running `wiki-graph.py` only re-scans changed files.
- **Ingest**: When Hermes ingests a source, it checks if the raw file hash has changed. If unchanged, it skips re-extraction.

## File Formats

### HERMES.md (Schema)

Template at `templates/HERMES.md.tpl`. Contains:
- Wiki topic/scope
- Page naming conventions
- Frontmatter schema
- Custom workflows

### index.md

```markdown
# Wiki Index

Last updated: YYYY-MM-DD

## Statistics
- Total pages: 0
- Sources: 0
- Entities: 0
- Concepts: 0
- Analysis: 0

## Entities (0)
- [[Entity Name]] - one line description

## Concepts (0)
- [[Concept Name]] - one line description

## Sources (0)
- [[Source Title]] - one line description

## Analysis (0)
- [[Analysis Title]] - one line description
```

### log.md

```markdown
# Wiki Log

## [YYYY-MM-DD HH:MM] ingest | Source Title
- Created [[Source Title]] summary
- Updated [[Entity A]], [[Concept B]]
- Added 3 new cross-references

## [YYYY-MM-DD HH:MM] graph | Knowledge graph built
- 15 nodes, 42 edges, 2 communities
- 3 orphan nodes detected

## [YYYY-MM-DD HH:MM] lint | Health check
- Found 2 orphan pages
- Fixed 1 broken link
```

### Source Page (sources/)

```markdown
---
type: source
date: YYYY-MM-DD
url: https://... (if applicable)
tags: [tag1, tag2]
---

# Source Title

## Summary
[2-3 sentence summary]

## Key Points
- Point 1
- Point 2

## Entities Mentioned
- [[Entity A]]
- [[Entity B]]

## Concepts Mentioned
- [[Concept X]]
- [[Concept Y]] (inferred)

## Related Sources
- [[Other Source]]
```

### Entity Page (entities/)

```markdown
---
type: entity
category: person|company|project|other
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Entity Name

## Overview
[Brief description]

## Key Facts
- Fact 1
- Fact 2

## Related Entities
- [[Other Entity]]

## Mentioned In
- [[Source A]]
- [[Source B]]
```

### Concept Page (concepts/)

```markdown
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Concept Name

## Definition
[Clear definition]

## Key Aspects
- Aspect 1: explanation

## Related Concepts
- [[Concept X]]
- [[Concept Y]] (inferred)

## Sources
- [[Source A]]
```

## Integration with Hermes

### Memory

When a wiki is initialized, save to memory:
```
User has an LLM wiki at {path} covering {topic}
```

### Trigger Detection

This skill should activate when:
- User mentions "wiki" + query/action
- User asks to "ingest" something
- User asks about the wiki's topic (if known)
- Working directory is inside a wiki
- User asks to "build graph", "query graph", or check wiki health

### Tools Used

- `read_file` - Read wiki pages
- `write_file` - Create/update pages
- `patch` - Update existing pages
- `search_files` - Search wiki content
- `web_extract` - Download URLs to raw/
- `vision_analyze` - Analyze images in raw/images/
- `terminal` - Run wiki-graph.py, wiki-query.py, wiki-lint

### Scripts

| Script | Purpose |
|--------|---------|
| `wiki-init.sh` | Initialize a new wiki directory |
| `wiki-ingest.sh` | Helper to copy files/URLs to raw/ |
| `wiki-lint.sh` | Comprehensive health check |
| `wiki-graph.py` | Build knowledge graph from wiki pages |
| `wiki-query.py` | Query the knowledge graph |

## Batch Ingest from Project Folder

When converting an existing project folder into a wiki:

1. **Initialize**: `wiki-init.sh <path> "<name>" "<topic>" "<scope>"`
2. **Read all source files** and classify into sources/entities/concepts
3. **Generate source pages** first — each raw doc gets a summary with extracted entities and concepts
4. **Generate entity pages** — people, projects, organizations with cross-references using `[[wikilinks]]`
5. **Generate concept pages** — key terms, methods, technologies with definitions and relations
6. **Generate analysis pages** — cross-cutting insights that synthesize multiple sources
7. **Annotate relations** with confidence levels (inferred/uncertain where appropriate)
8. **Update index.md** with page counts and one-line descriptions
9. **Append to log.md** with timestamp and summary of what was created
10. **Build graph**: Run `wiki-graph.py --report` to generate graph.json and GRAPH_REPORT.md

Use `execute_code` to batch-generate pages efficiently (one write_file call per page, grouped by type).

Pitfall: A single source typically touches 5-15 wiki pages. Plan for entity/concept extraction upfront to avoid re-reading sources.

## Pitfalls

1. **Confidence annotation format**: `(inferred, description)` is NOT recognized by wiki-graph.py. The regex `\[\[(.+?)\]\]\s*(?:\(inferred|uncertain\))?` only matches bare `(inferred)` or `(uncertain)`. Any extra text inside the parentheses causes silent fallback to EXTRACTED. Always use `[[X]] (inferred)` and put explanatory text outside the parentheses.

2. **wiki-lint.sh zsh incompatibility**: On macOS zsh, the orphan check loop (`for file in "$WIKI_PATH/$dir"/*.md 2>/dev/null`) fails with a syntax error. Workaround: use `execute_code` with Python to run health checks instead, or run lint under `bash` explicitly.

3. **Scripts not in wiki root**: wiki-graph.py and other scripts live in `~/.hermes/skills/llm-wiki/scripts/`, not in the wiki directory. Either copy them to the wiki root or reference the full path with `--wiki-path`.

4. **Batch page creation**: When ingesting a source that creates 10+ pages, use `execute_code` with a Python dict of page contents and loop over `write_file` calls. This is much faster than individual tool calls. Plan entity/concept extraction upfront to avoid re-reading the source.

5. **Orphan pages after batch creation**: When creating many new concept/entity pages in one session, some may end up as orphans (no other page links to them). Always run a health check after batch operations and add backlinks from relevant hub pages (usually the core concept page or source summaries).

## Tips

1. **Obsidian Web Clipper** - Use browser extension to save articles to raw/
2. **Download images** - In Obsidian, Ctrl+Shift+D to download images locally
3. **Graph view** - Use Obsidian's graph view OR run `wiki-graph.py --report` for the Hermes-native version
4. **Git** - The wiki is just markdown files, version control with git
5. **Skill visibility** - This skill may not appear in `skills_list` but exists at `~/.hermes/skills/llm-wiki/`. If a user asks for it, search the filesystem.
6. **Graph freshness** - wiki-query.py auto-rebuilds the graph if it's >24h old. Use `--no-auto-build` to skip.
