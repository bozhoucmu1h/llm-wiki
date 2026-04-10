# Contributing to LLM Wiki

Thanks for your interest! This is a Hermes Agent skill — contributions are welcome.

## How to Contribute

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** and test with a real wiki
4. **Commit**: `git commit -m "Add your feature"`
5. **Push**: `git push origin feature/your-feature`
6. **Open a Pull Request**

## Areas for Contribution

- 🐛 **Bug fixes** — especially the wiki-lint.sh zsh compatibility issue
- ✨ **New graph algorithms** — PageRank, centrality, graph embeddings
- 📊 **Visualization** — HTML/interactive graph viewer from graph.json
- 🔄 **Export formats** — Export wiki to Notion, Confluence, HTML site
- 🌐 **Web UI** — A simple web interface for browsing the wiki
- 📝 **More templates** — Templates for specific domains (bio, CS, law, etc.)

## Development Setup

```bash
# Clone the skill
git clone https://github.com/bozhoucmu1h/llm-wiki.git
cd llm-wiki

# Test the graph builder
python3 scripts/wiki-graph.py --wiki-path /path/to/test/wiki --report

# Test the query engine
python3 scripts/wiki-query.py --wiki-path /path/to/test/wiki hubs
```

## Reporting Issues

Please open a GitHub issue with:
- What you were doing
- What you expected to happen
- What actually happened
- Wiki structure (if relevant)
