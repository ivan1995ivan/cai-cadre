<#
  Strânge pachetul pentru serverul Linux (Docker) din commit-ul curent:
    powershell -ExecutionPolicy Bypass -File tools\make_docker_package.ps1
  → releases\cai-cadre-docker-<versiune>.tar.gz; pe server: tar xzf ...; cd cai-cadre-<versiune>; sh install.sh
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$version = (Select-String -Path (Join-Path $root "backend\config\settings.py") -Pattern 'APP_VERSION = "([^"]+)"').Matches[0].Groups[1].Value
$out = Join-Path $root "releases\cai-cadre-docker-$version.tar.gz"
New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
git -C $root archive --format=tar.gz --prefix="cai-cadre-$version/" -o $out HEAD `
  Dockerfile docker-compose.yml .dockerignore .env.example install.sh backend frontend docs
if ($LASTEXITCODE -ne 0) { throw "git archive" }
Write-Host "Gata: $out"
