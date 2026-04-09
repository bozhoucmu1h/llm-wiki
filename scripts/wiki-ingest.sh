#!/bin/bash
# Helper script to copy a file to raw/ and report path

WIKI_PATH="${LLM_WIKI_PATH:-$HOME/wiki}"
SOURCE="$1"

if [ -z "$SOURCE" ]; then
    echo "Usage: wiki-ingest <file-or-url>"
    exit 1
fi

if [ ! -d "$WIKI_PATH" ]; then
    echo "Error: Wiki not found at $WIKI_PATH"
    exit 1
fi

# URL
if [[ "$SOURCE" =~ ^https?:// ]]; then
    echo "URL detected. Tell Hermes:"
    echo "  'Download $SOURCE to the wiki raw/ folder and ingest it'"
    exit 0
fi

# Local file
if [ -f "$SOURCE" ]; then
    FILENAME=$(basename "$SOURCE")
    DEST="$WIKI_PATH/raw/other/$FILENAME"
    cp "$SOURCE" "$DEST"
    echo "File copied to: $DEST"
    echo ""
    echo "Tell Hermes:"
    echo "  'Ingest $DEST into the wiki'"
else
    echo "Error: File not found: $SOURCE"
    exit 1
fi
