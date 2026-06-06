#!/usr/bin/env sh
set -e
files=$(git ls-files '*.py')
ruff format $files
basedpyright $files
