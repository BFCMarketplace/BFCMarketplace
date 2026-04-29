# Obsidian Vault Setup Script - ElectroGestion / BFC Marketplace / Amazon FBA
# Run as: powershell -ExecutionPolicy Bypass -File setup.ps1
# Requires: Windows PowerShell 5.1+ sau PowerShell 7+

param(
    [string]$VaultPath = "$env:USERPROFILE\Documents\ObsidianVault",
    [string]$AnthropicApiKey = ""
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Obsidian Vault Setup - Claude Workspace" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Validate API key
if ([string]::IsNullOrEmpty($AnthropicApiKey)) {
    $AnthropicApiKey = Read-Host "Introdu Anthropic API Key (sk-ant-...)"
}
if (-not $AnthropicApiKey.StartsWith("sk-ant-")) {
    Write-Warning "API Key pare invalida. Continui oricum..."
}

Write-Host "Vault path: $VaultPath" -ForegroundColor Yellow
Write-Host ""

# Create folder structure
$folders = @(
    ".obsidian\plugins\claude-connector",
    "00-Dashboard",
    "01-ElectroGestion\Projects",
    "01-ElectroGestion\Meetings",
    "01-ElectroGestion\Tasks",
    "01-ElectroGestion\Reports",
    "02-BFC-Marketplace\Products",
    "02-BFC-Marketplace\Orders",
    "02-BFC-Marketplace\Analytics",
    "02-BFC-Marketplace\Listings",
    "03-Amazon-FBA\Inventory",
    "03-Amazon-FBA\Listings",
    "03-Amazon-FBA\Finances",
    "03-Amazon-FBA\Reports",
    "Templates",
    "Archive"
)

Write-Host "Creez structura de foldere..." -ForegroundColor Green
foreach ($folder in $folders) {
    $fullPath = Join-Path $VaultPath $folder
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  + $folder" -ForegroundColor DarkGray
    } else {
        Write-Host "  = $folder (exista deja)" -ForegroundColor DarkGray
    }
}

# Copy plugin files from script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginSource = Join-Path $scriptDir ".obsidian\plugins\claude-connector"
$pluginDest = Join-Path $VaultPath ".obsidian\plugins\claude-connector"

Write-Host ""
Write-Host "Copiez plugin-ul Claude Connector..." -ForegroundColor Green
if (Test-Path $pluginSource) {
    Copy-Item -Path "$pluginSource\*" -Destination $pluginDest -Force
    Write-Host "  Plugin copiat cu succes" -ForegroundColor DarkGray
} else {
    Write-Warning "Fisierele plugin nu au fost gasite langa script. Copiaza manual folderul .obsidian\"
}

# Copy obsidian config files
$configFiles = @("app.json", "community-plugins.json", "hotkeys.json")
$obsidianSrc = Join-Path $scriptDir ".obsidian"
$obsidianDest = Join-Path $VaultPath ".obsidian"
foreach ($cfg in $configFiles) {
    $src = Join-Path $obsidianSrc $cfg
    if (Test-Path $src) {
        Copy-Item $src $obsidianDest -Force
        Write-Host "  + Config: $cfg" -ForegroundColor DarkGray
    }
}

# Copy template and note files
Write-Host ""
Write-Host "Copiez template-uri si note initiale..." -ForegroundColor Green
$noteFolders = @("00-Dashboard","01-ElectroGestion","02-BFC-Marketplace","03-Amazon-FBA","Templates")
foreach ($nf in $noteFolders) {
    $src = Join-Path $scriptDir $nf
    $dst = Join-Path $VaultPath $nf
    if (Test-Path $src) {
        Get-ChildItem $src -Filter "*.md" | ForEach-Object {
            Copy-Item $_.FullName $dst -Force
            Write-Host "  + $nf\$($_.Name)" -ForegroundColor DarkGray
        }
    }
}

# Write plugin settings with API key
$pluginDataPath = Join-Path $VaultPath ".obsidian\plugins\claude-connector\data.json"
$pluginData = @{
    apiKey        = $AnthropicApiKey
    model         = "claude-sonnet-4-6"
    maxTokens     = 4096
    temperature   = 0.7
    enableCaching = $true
    activeProject = "BFC-Marketplace"
    projects      = @{
        "ElectroGestion"  = @{ enabled = $true; color = "#4CAF50" }
        "BFC-Marketplace" = @{ enabled = $true; color = "#2196F3" }
        "Amazon-FBA"      = @{ enabled = $true; color = "#FF9800" }
    }
} | ConvertTo-Json -Depth 5

$pluginData | Set-Content -Path $pluginDataPath -Encoding UTF8
Write-Host ""
Write-Host "Configuratie plugin scrisa (cu API key)" -ForegroundColor Green

# Save API key to Windows Credential Manager (optional, safer storage)
try {
    $secureKey = ConvertTo-SecureString $AnthropicApiKey -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential("ObsidianClaudeConnector", $secureKey)
    # cmdkey alternative for basic storage
    Write-Host "Tip: Poti stoca API key-ul si in Windows Credential Manager pentru securitate mai buna" -ForegroundColor Yellow
} catch {}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Setup complet!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Urmatori pasi:" -ForegroundColor White
Write-Host "  1. Deschide Obsidian -> 'Open folder as vault' -> $VaultPath" -ForegroundColor Gray
Write-Host "  2. Settings -> Community plugins -> Enable 'Claude Connector'" -ForegroundColor Gray
Write-Host "  3. Apasa Ctrl+P -> 'Claude: Ask' pentru a incepe" -ForegroundColor Gray
Write-Host ""
