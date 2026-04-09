#!/bin/bash
# Search wiki content

WIKI_PATH="${LLM_WIKI_PATH:-$HOME/wiki}"
QUERY="$*"

if [ -z "$QUERY" ]; then
    echo "Usage: wiki-search <query>"
    exit 1
fi

if [ ! -d "$WIKI_PATH" ]; then
    echo "Error: Wiki not found at $WIKI_PATH"
    echo "Set LLMS_WIKI_PATH or create a wiki with wiki-init"
    exit 1
fi

echo "Searching wiki for: $QUERY"
echo "---"

# Search in markdown files, show filename and matching lines
grep -rli --include="*.md" "$QUERY" "$WIKI_PATH" 2>/dev/null | while read -r file; do
    rel_path="${file#$WIKI_PATH/}"
    echo "📄 $rel_path"
    grep -ni --include="*.md" "$QUERY" "$file" 2>/dev/null | head -3
    echo ""
done
