#!/usr/bin/env sh
set -e
files=$(git ls-files --cached --others --exclude-standard -- '*.py' | while IFS= read -r file; do
    if [ -e "$file" ]; then
        printf '%s\n' "$file"
    fi
done)
ruff check --fix --select F401 $files
ruff format $files
basedpyright $files
