<#
.SYNOPSIS
    MiganCore — One-line MCP setup for Claude Code CLI on Windows

.DESCRIPTION
    Logs in to MiganCore, creates a long-lived API key, and registers it
    with Claude Code so MiganCore tools are always available.

.EXAMPLE
    iwr https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.ps1 | iex

.EXAMPLE
    .\migan-setup.ps1 -Email you@example.com -Password 'secret'
#>
param(
    [string]$Email = $env:MIGAN_EMAIL,
    [string]$Password = $env:MIGAN_PASSWORD,
    [string]$ApiBase = $(if ($env:MIGAN_API) { $env:MIGAN_API } else { "https://api.migancore.com" }),
    [string]$ServerName = $(if ($env:MIGAN_SERVER_NAME) { $env:MIGAN_SERVER_NAME } else { "migancore" }),
    [string]$KeyName = $(if ($env:MIGAN_KEY_NAME) { $env:MIGAN_KEY_NAME } else { "claude-code-$($env:COMPUTERNAME)" })
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "▸ $msg" -ForegroundColor White }
function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

Write-Step "MiganCore — One-line MCP setup"
Write-Host ""

# Detect claude CLI
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($null -eq $claudeCmd) {
    Write-Warn2 "Claude Code CLI ('claude') not found in PATH"
    Write-Warn2 "Install: https://docs.claude.com/en/docs/claude-code"
    Write-Warn2 "Or proceed manually using the API key shown at the end."
    $claudeOk = $false
} else {
    $claudeOk = $true
    Write-Ok "Claude Code CLI found: $($claudeCmd.Source)"
}

# Get credentials
if (-not $Email) { $Email = Read-Host "MiganCore email" }
if (-not $Password) {
    $secure = Read-Host "MiganCore password" -AsSecureString
    $Password = [System.Net.NetworkCredential]::new("", $secure).Password
}
if (-not $Email -or -not $Password) { Write-Fail "Email and password required" }

# Login
Write-Step "Logging in as $Email..."
try {
    $loginBody = @{ email = $Email; password = $Password } | ConvertTo-Json -Compress
    $loginResp = Invoke-RestMethod -Method POST -Uri "$ApiBase/v1/auth/login" `
        -ContentType "application/json" -Body $loginBody
} catch {
    Write-Fail "Login failed: $($_.Exception.Message)"
}

$jwt = $loginResp.access_token
if (-not $jwt) { Write-Fail "No access_token in login response" }
Write-Ok "JWT obtained"

# Create API key
Write-Step "Creating long-lived API key '$KeyName'..."
try {
    $keyBody = @{ name = $KeyName } | ConvertTo-Json -Compress
    $keyResp = Invoke-RestMethod -Method POST -Uri "$ApiBase/v1/api-keys" `
        -Headers @{ "Authorization" = "Bearer $jwt" } `
        -ContentType "application/json" -Body $keyBody
} catch {
    Write-Fail "API key creation failed: $($_.Exception.Message)"
}

$apiKey = $keyResp.key
$keyId = $keyResp.id
$prefix = $keyResp.prefix
if (-not $apiKey) { Write-Fail "No 'key' in API key response" }
Write-Ok "API key created: $prefix..."

# Register with Claude Code
if ($claudeOk) {
    Write-Step "Registering with Claude Code..."
    & claude mcp remove $ServerName 2>$null
    $regResult = & claude mcp add --transport http $ServerName "$ApiBase/mcp/" `
        --header "Authorization: Bearer $apiKey" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Registered as '$ServerName' in Claude Code"
    } else {
        Write-Warn2 "Auto-registration failed. Run manually:"
        Write-Host "    claude mcp add --transport http $ServerName $ApiBase/mcp/ \"
        Write-Host "      --header `"Authorization: Bearer $apiKey`""
    }
}

# Final report
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Setup complete" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  API key (save this if you want to use elsewhere):"
Write-Host "    $apiKey"
Write-Host ""
Write-Host "  Manage keys at: $ApiBase/v1/api-keys"
Write-Host "  Revoke this key:"
Write-Host "    Invoke-RestMethod -Method DELETE -Uri '$ApiBase/v1/api-keys/$keyId' -Headers @{Authorization='Bearer <login-jwt>'}"
Write-Host ""
if ($claudeOk) {
    Write-Host "  Try it: open Claude Code and ask"
    Write-Host '    "buatkan gambar logo MiganCore"'
    Write-Host '    "tulis file todo.md isinya belajar React"'
}
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
