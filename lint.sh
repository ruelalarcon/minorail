#!/usr/bin/env sh
set -e
files=$(git ls-files --cached --others --exclude-standard -- '*.py')
ruff check --fix --select F401 $files
ruff format $files
basedpyright $files
