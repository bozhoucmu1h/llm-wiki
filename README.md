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
```bash
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
[[AGI]] (uncertain)                ← Needs verification
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

## 🎬 Demo: AI History Wiki

A real example built with 3 source articles on AI history — producing a rich, interconnected knowledge base:

### Input → Output

```
3 source articles (AI history, deep learning, LLM frontier)
         │
         ▼  LLM extracts entities + concepts
    ┌─────────────────────────────────────────┐
    │  Sources:   3                           │
    │  Entities:  22  (pioneers, labs, systems)│
    │  Concepts:  41  (algorithms, models, ...) │
    │  Analysis:  1   (cross-paper synthesis)  │
    │  ─────────────────────────────────────── │
    │  Total:     67 wiki pages                │
    └─────────────────────────────────────────┘
         │
         ▼  wiki-graph.py scans [[wikilinks]]
    ┌─────────────────────────────────────────┐
    │  Knowledge Graph                         │
    │  Nodes:        76                        │
    │  Edges:        469                       │
    │  Communities:  6                         │
    │  Confidence:   354 EXTRACTED (75.5%)     │
    │               115 INFERRED  (24.5%)      │
    └─────────────────────────────────────────┘
```

### Hub Nodes (Most Connected)

The graph automatically identifies the most central concepts:

| # | Node | Connections | Type | Why it's a hub |
|---|------|:-----------:|------|----------------|
| 1 | **深度学习革命** | 77 | source | Covers CNN, RNN, Transformer, GAN |
| 2 | **人工智能简史** | 72 | source | Spans 70 years of AI milestones |
| 3 | **大语言模型前沿** | 48 | source | LLM landscape, alignment, open source |
| 4 | **Transformer** | 35 | concept | Foundation of modern NLP & LLMs |
| 5 | **大语言模型** | 30 | concept | Core concept linking many models |
| 6 | **AI范式演进** | 28 | analysis | Cross-paper synthesis page |
| 7 | **神经网络** | 28 | concept | Foundational concept, links to all variants |
| 8 | **杰弗里·辛顿** | 25 | entity | Deep learning pioneer, connects people & ideas |
| 9 | **OpenAI** | 22 | entity | Links GPT, ChatGPT, RLHF, people |
| 10 | **GPT系列** | 21 | concept | Connects models, training, alignment |

### Auto-Detected Communities

The graph discovered 6 communities — a main cluster of 71 tightly connected nodes (the core AI/deep learning domain), plus 5 singleton nodes at the periphery that bridge specialized sub-topics:

- **Community 4 (71 nodes)**: Core AI knowledge — everything from neural networks to LLMs
- **Community 0 (1 node)**: GPT-2 — specific model variant
- **Community 1 (1 node)**: GPT-3 — specific model variant
- **Community 2 (1 node)**: GPT-4 — specific model variant
- **Community 3 (1 node)**: 杰明·萨顿 — niche researcher reference
- **Community 5 (1 node)**: Seq2Seq — specific architecture variant

### What This Demonstrates

- **3 articles → 67 pages**: Each source touches 15-25 wiki pages as the LLM decomposes it
- **469 edges from wikilinks**: Dense interconnections that make exploration possible
- **75.5% EXTRACTED + 24.5% INFERRED**: Clear separation between source-grounded and LLM-deduced knowledge
- **Hub analysis reveals importance**: Transformer (35 connections) is more central than any single person — a data-driven insight

> 📂 The full demo wiki is in `examples/ai-history-wiki/` — open it in Obsidian to see the interactive graph view.

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
date: 2026-04-10
tags: [AI, history]
---

# Paper Title

## Summary
2-3 sentence overview...

## Key Findings
- Finding 1
- Finding 2

## Entities Mentioned
- [[Person A]]
- [[Organization B]]

## Concepts Mentioned
- [[Method X]]
- [[Framework Y]] (inferred)
```

### Entity (`entities/`)
```markdown
---
type: entity
category: person
created: 2026-04-10
updated: 2026-04-10
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
created: 2026-04-10
updated: 2026-04-10
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
