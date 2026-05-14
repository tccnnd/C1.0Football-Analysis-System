param($path)
(Get-Content -LiteralPath $path) -replace '^pick 505d01d ', 'edit 505d01d ' | Set-Content -LiteralPath $path
