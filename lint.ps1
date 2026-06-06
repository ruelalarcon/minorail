Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$files = git ls-files '*.py'
ruff format $files
basedpyright $files
