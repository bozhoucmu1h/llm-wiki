<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/Zero_Deps-Standard_Library-success.svg" alt="No Dependencies" />
  <img src="https://img.shields.io/badge/Obsidian-Compatible-purple?logo=obsidian&logoColor=white" alt="Obsidian" />
</p>

<h1 align="center">📖 LLM Wiki</h1>

<p align="center">
  <strong>Build a compounding knowledge base with your AI agent — not a disposable RAG.</strong>
</p>

<p align="center">
  <a href="#-what-is-it">What</a> ·
  <a href="#-why-not-rag">Why</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-knowledge-graph">Graph</a> ·
  <a href="#-demo">Demo</a> ·
  <a href="#-architecture">Architecture</a>
</p>

---

## 🤔 What is it

**LLM Wiki** is a skill for [Hermes Agent](https://github.com/bozhoucmu1h/hermes) that turns raw documents into a **structured, interconnected knowledge base** — with an auto-generated knowledge graph, confidence tracking, and graph-based queries.

You feed it papers, articles, reports. The LLM extracts entities and concepts, creates wiki pages with `[[wikilinks]]`, and annotates relationships with confidence levels. A built-in Python script then builds a **knowledge graph** (graph.json) from those wikilinks — no external databases, no vector stores, no complex setup.

> **Designed for**: Researchers, students, and anyone who accumulates knowledge across sessions and wants it to compound over time.

## 🤷 Why not RAG

| | RAG | LLM Wiki |
|---|---|---|
| **Knowledge lifecycle** | Re-derived every query | Compiled once, kept current |
| **Cross-session memory** | Lost when context resets | Persistent markdown files |
| **Relationships** | Implicit in embeddings | Explicit `[[wikilinks]]` with confidence |
| **Explorability** | Black-box similarity search | Browsable wiki + knowledge graph |
| **Tooling** | Vector DB + embedding model | Plain markdown + Python stdlib |
| **Version control** | Hard | `git init` and you're done |
| **Human readability** | Chunked text | Structured wiki pages |

**RAG answers questions. LLM Wiki builds understanding.**

## ✨ Key Features

### 🧠 LLM-Powered Extraction
Feed any source (PDF, URL, local file) and the LLM automatically:
- Creates a **source summary** with key findings
- Extracts **entities** (people, organizations, journals) with descriptions
- Extracts **concepts** (methods, metrics, frameworks) with definitions
- Links everything together with `[[wikilinks]]`

### 🕸️ Knowledge Graph (Zero Dependencies)
```
wiki-graph.py --wiki-path ./my-wiki --report
```
- Scans all wiki pages and builds `graph.json`
- **Community detection** — auto-discovers topic clusters
- **Hub node analysis** — identifies the most connected concepts
- **Confidence tracking** — distinguishes EXTRACTED vs INFERRED relations
- **Incremental updates** — SHA256 cache, only re-scans changed files
- **No dependencies** — pure Python standard library

### 📍 Confidence Annotations
Every `[[wikilink]]` can be annotated:

```markdown
[[Transformer]]                    ← EXTRACTED (directly from source)
[[BERT]] (inferred)                ← LLM deduced this connection
[[GPT-5]] (uncertain)              ← Needs verification
```

The graph tracks confidence per edge, so you can:
- Filter out speculative connections
- Prioritize verification of inferred links
- Track how your knowledge grows over time

### 🔍 Graph Queries
```bash
# Shortest path between two concepts
wiki-query.py path "GPT" "BERT"

# All connections of a node
wiki-query.py neighbors "Transformer"

# Community members
wiki-query.py community "Self-Attention"

# Top hub nodes
wiki-query.py hubs

# Search by keyword
wiki-query.py search "attention"
```

### 🏥 Health Checks
```bash
wiki-lint
```
Checks for orphan pages, stale content, missing index entries, duplicate pages, and graph status.

### 👀 Obsidian Compatible
The entire wiki is plain markdown with `[[wikilinks]]` — open it in Obsidian for a rich visual experience, or use the built-in graph tools.

## 🚀 Quick Start

### 1. Initialize a wiki
```bash
bash wiki-init.sh ~/my-wiki "My Wiki" "Topic" "Scope description"
```

This creates the directory structure:
```
my-wiki/
├── HERMES.md          # Schema — tells the LLM how to work with this wiki
├── index.md           # Content catalog
├── log.md             # Timeline log
├── raw/               # Source documents (immutable)
│   ├── articles/
│   ├── papers/
│   └── images/
├── sources/           # Source summaries (one per raw doc)
├── entities/          # Entity pages (people, companies, projects)
├── concepts/          # Concept pages (topics, technologies, themes)
├── analysis/          # Analysis, comparisons, synthesis
└── .cache/            # SHA256 hashes for incremental updates
```

### 2. Ingest sources
Tell your AI agent: *"Ingest this paper into the wiki"*

The LLM will:
1. Save the raw document to `raw/`
2. Create a source summary in `sources/`
3. Extract entities → `entities/`
4. Extract concepts → `concepts/`
5. Annotate relations with confidence
6. Update `index.md` and `log.md`

### 3. Build the knowledge graph
```bash
python3 wiki-graph.py --wiki-path ~/my-wiki --report
```

Outputs:
- `graph.json` — full graph data (nodes, edges, communities, hubs)
- `GRAPH_REPORT.md` — human-readable analysis with hub nodes, communities, suggested questions, orphan detection

### 4. Query and explore
```bash
python3 wiki-query.py neighbors "Concept Name"
python3 wiki-query.py path "Node A" "Node B"
python3 wiki-query.py hubs
```

Or just ask your AI agent: *"What connects X and Y in the wiki?"*

## 🎬 Demo: PBRTQC Research Wiki

A real example — 2 literature review documents on Patient-Based Real-Time Quality Control (PBRTQC) in clinical chemistry were ingested, producing:

### Wiki Statistics
```
Sources:   2     ← Literature reviews
Entities:  8     ← Hospitals, journals, institutions
Concepts:  18    ← Methods, metrics, frameworks
Analysis:  1     ← Cross-paper method comparison
─────────────────
Total:     29 pages from 2 source documents
```

### Knowledge Graph
```
Nodes:        29
Edges:        191
Communities:  6
Confidence:   127 EXTRACTED (66.5%) · 64 INFERRED (33.5%)
```

### Hub Nodes (Most Connected)
| Node | Connections | Type |
|------|:-----------:|------|
| PBRTQC文献调研报告_系统间比对专题 | 46 | source |
| PBRTQC文献研读汇报 | 44 | source |
| **PBRTQC** | 29 | concept |
| **EWMA** | 23 | concept |
| **DMI** | 17 | concept |
| mNL-PBRTQC | 15 | concept |
| 双模块比值法 | 15 | concept |
| 北京朝阳医院 | 13 | entity |

### Auto-Detected Communities
The graph discovered 6 communities — a main cluster of 24 tightly connected nodes (the core PBRTQC research domain), plus 4 singleton nodes at the periphery (CART算法, Winsorization, ADQC, EQA) that bridge different sub-topics.

### Generated GRAPH_REPORT.md Sections
1. **Overview** — Node/edge/community counts + confidence breakdown
2. **Hub Nodes** — Top 10 most-connected pages
3. **Communities** — Auto-detected clusters with member lists
4. **Unexpected Connections** — Cross-community edges (interesting bridges)
5. **Orphan Nodes** — Pages with no connections
6. **Suggested Questions** — Auto-generated research questions from graph structure
7. **Stale Pages** — Pages not updated in 30+ days

> 📸 *Open this wiki in Obsidian's Graph View to see the full interactive visualization.*

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER / AGENT                          │
│  "Ingest this paper"  "What connects X and Y?"  "Lint wiki" │
└─────────────┬───────────────────┬──────────────────┬─────────┘
              │                   │                  │
              ▼                   ▼                  ▼
     ┌────────────────┐  ┌──────────────┐  ┌──────────────┐
     │   INGEST PIPE  │  │  GRAPH QUERY │  │   HEALTH     │
     │                │  │              │  │   CHECK      │
     │ 1. Read source │  │ wiki-query.py│  │ wiki-lint.sh │
     │ 2. Extract     │  │              │  │              │
     │ 3. Create pages│  │ • path       │  │ • orphans    │
     │ 4. Annotate    │  │ • neighbors  │  │ • stale      │
     │    confidence  │  │ • community  │  │ • duplicates │
     │ 5. Update index│  │ • hubs       │  │ • coverage   │
     └───────┬────────┘  └──────┬───────┘  └──────────────┘
             │                  │
             ▼                  ▼
     ┌────────────────────────────────────┐
     │         WIKI DIRECTORY             │
     │                                    │
     │  sources/*.md  entities/*.md       │
     │  concepts/*.md analysis/*.md       │
     │         ↓ [[wikilinks]] ↓          │
     │  ┌──────────────────────────┐      │
     │  │   wiki-graph.py          │      │
     │  │   ──────────────────     │      │
     │  │   Parse markdown         │      │
     │  │   Extract wikilinks      │      │
     │  │   Build graph            │      │
     │  │   Detect communities     │      │
     │  │   Find hubs              │      │
     │  │   Zero external deps     │      │
     │  └──────────┬───────────────┘      │
     │             ▼                       │
     │      graph.json                    │
     │      GRAPH_REPORT.md               │
     └────────────────────────────────────┘
             │
             ▼
     ┌──────────────┐     ┌──────────────┐
     │   Obsidian    │     │     Git      │
     │   (optional)  │     │   (optional) │
     │   Graph View  │     │   Version    │
     │   Backlinks   │     │   Control    │
     └──────────────┘     └──────────────┘
```

## 📁 Scripts

| Script | Purpose |
|--------|---------|
| `scripts/wiki-init.sh` | Initialize a new wiki directory |
| `scripts/wiki-ingest.sh` | Helper to copy files/URLs to raw/ |
| `scripts/wiki-graph.py` | Build knowledge graph + generate report |
| `scripts/wiki-query.py` | Query the graph (path, neighbors, community, hubs, search) |
| `scripts/wiki-search.sh` | Quick text search across all wiki pages |
| `scripts/wiki-lint.sh` | Comprehensive health check |

## 📦 Page Types

### Source (`sources/`)
```markdown
---
type: source
date: 2026-03-05
tags: [PBRTQC, quality-control]
---

# Paper Title

## Summary
2-3 sentence overview...

## Key Findings
- Finding 1
- Finding 2

## Entities Mentioned
- [[Hospital A]]
- [[Journal B]]

## Concepts Mentioned
- [[Method X]]
- [[Framework Y]] (inferred)
```

### Entity (`entities/`)
```markdown
---
type: entity
category: institution
created: 2026-03-05
updated: 2026-03-05
---

# Entity Name

## Overview
Brief description...

## Key Contributions
- Contribution 1

## Related Entities
- [[Other Entity]] (inferred)
```

### Concept (`concepts/`)
```markdown
---
type: concept
created: 2026-03-05
updated: 2026-03-05
---

# Concept Name

## Definition
Clear definition...

## Key Aspects
- Aspect 1: explanation

## Related Concepts
- [[Related Concept]] (inferred)
```

## 🔧 Requirements

- **Python 3.10+** (for graph scripts)
- **Bash** (for init/lint scripts)
- **Hermes Agent** (for LLM-powered ingest)
- **Obsidian** (optional, for visual exploration)

No pip installs. No vector databases. No embedding models. **Zero external dependencies.**

## 📄 License

MIT

---

<p align="center">
  Built for <a href="https://github.com/bozhoucmu1h/hermes">Hermes Agent</a> · 
  Works with <a href="https://obsidian.md">Obsidian</a> · 
  Powered by Markdown
</p>
