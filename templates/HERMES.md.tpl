# {WIKI_NAME} - Wiki Schema

This file tells LLMs how to work with this wiki.

## Topic

{WIKI_TOPIC}

## Scope

{WIKI_SCOPE}

## Naming Conventions

- **Sources**: Use article/document title, slugified
- **Entities**: Use canonical name (e.g., "OpenAI" not "openai")
- **Concepts**: Use clear, searchable names

## Page Types

| Type | Directory | Purpose |
|------|-----------|---------|
| source | sources/ | Summary of a raw document |
| entity | entities/ | A person, company, project, etc. |
| concept | concepts/ | A topic, technology, or theme |
| analysis | analysis/ | Comparisons, synthesis, insights |

## Frontmatter Schema

All pages should include:
```yaml
---
type: source|entity|concept|analysis
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
---
```

## Workflows

### Ingest New Source

1. Save raw document to `raw/` (preserve original)
2. Create summary in `sources/`
3. Extract entities → create/update in `entities/`
4. Extract concepts → create/update in `concepts/`
5. Update `index.md`
6. Append to `log.md`

### Answer Questions

1. Read `index.md` to find relevant pages
2. Read relevant pages in detail
3. Synthesize answer with [[citations]]
4. If answer is valuable, file as new page in `analysis/`

### Maintain Wiki

1. Run lint periodically
2. Fix orphan pages by adding links
3. Update stale information
4. Merge duplicate concepts

## Custom Rules

{CUSTOM_RULES}
