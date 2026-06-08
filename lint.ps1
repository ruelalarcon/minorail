Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$files = git ls-files --cached --others --exclude-standard -- '*.py' | Where-Object {
    Test-Path -LiteralPath $_
}
ruff check --fix --select F401 $files
ruff format $files
basedpyright $files
