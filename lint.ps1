Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$files = git ls-files --cached --others --exclude-standard -- '*.py'
ruff check --fix --select F401 $files
ruff format $files
basedpyright $files
