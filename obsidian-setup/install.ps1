# Obsidian Vault - Install Script Standalone
# Ruleaza direct: powershell -ExecutionPolicy Bypass -File install.ps1

param([string]$VaultPath = "$env:USERPROFILE\Documents\ObsidianVault")

$ApiKey = Read-Host "Introdu Anthropic API Key (sk-ant-...)"

Write-Host "Creez vault la: $VaultPath" -ForegroundColor Cyan

# Foldere
@(
    ".obsidian\plugins\claude-connector",
    "00-Dashboard","01-ElectroGestion\Projects","01-ElectroGestion\Meetings",
    "01-ElectroGestion\Tasks","01-ElectroGestion\Reports",
    "02-BFC-Marketplace\Products","02-BFC-Marketplace\Orders",
    "02-BFC-Marketplace\Analytics","02-BFC-Marketplace\Listings",
    "03-Amazon-FBA\Inventory","03-Amazon-FBA\Listings",
    "03-Amazon-FBA\Finances","03-Amazon-FBA\Reports",
    "Templates","Archive"
) | ForEach-Object { New-Item -ItemType Directory -Path "$VaultPath\$_" -Force | Out-Null; Write-Host "  + $_" -ForegroundColor DarkGray }

# manifest.json
@'
{"id":"claude-connector","name":"Claude Connector","version":"1.2.0","minAppVersion":"1.4.0","description":"Claude AI pentru ElectroGestion, BFC Marketplace, Amazon FBA","author":"BFC Workspace","isDesktopOnly":true}
'@ | Set-Content "$VaultPath\.obsidian\plugins\claude-connector\manifest.json" -Encoding UTF8

# community-plugins.json
'["claude-connector"]' | Set-Content "$VaultPath\.obsidian\community-plugins.json" -Encoding UTF8

# app.json
@'
{"promptDelete":false,"trashOption":"local","livePreview":true,"theme":"obsidian","baseFontSize":16,"attachmentFolderPath":"Archive/attachments"}
'@ | Set-Content "$VaultPath\.obsidian\app.json" -Encoding UTF8

# hotkeys.json
@'
{"claude-connector:claude-open-chat":[{"modifiers":["Ctrl","Shift"],"key":"C"}],"claude-connector:claude-ask-selection":[{"modifiers":["Ctrl","Shift"],"key":"A"}],"claude-connector:claude-summarize-note":[{"modifiers":["Ctrl","Shift"],"key":"S"}]}
'@ | Set-Content "$VaultPath\.obsidian\hotkeys.json" -Encoding UTF8

# data.json (cu API key)
@"
{"apiKey":"$ApiKey","model":"claude-sonnet-4-6","maxTokens":4096,"temperature":0.7,"enableCaching":true,"activeProject":"BFC-Marketplace","maxHistoryMessages":10,"showTokenCount":true,"autoInsertResponse":false}
"@ | Set-Content "$VaultPath\.obsidian\plugins\claude-connector\data.json" -Encoding UTF8

Write-Host ""
Write-Host "Descarc plugin main.js de pe GitHub..." -ForegroundColor Green
try {
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/BFCMarketplace/BFCMarketplace/claude/obsidian-claude-setup-7mFsh/obsidian-setup/.obsidian/plugins/claude-connector/main.js" -OutFile "$VaultPath\.obsidian\plugins\claude-connector\main.js" -UseBasicParsing
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/BFCMarketplace/BFCMarketplace/claude/obsidian-claude-setup-7mFsh/obsidian-setup/.obsidian/plugins/claude-connector/styles.css" -OutFile "$VaultPath\.obsidian\plugins\claude-connector\styles.css" -UseBasicParsing
    Write-Host "  Plugin descarcat cu succes" -ForegroundColor DarkGray
} catch {
    Write-Warning "Nu am putut descarca plugin de pe GitHub. Copiaza manual main.js si styles.css in: $VaultPath\.obsidian\plugins\claude-connector\"
}

# Note
@'
# Dashboard Principal

## Proiecte Active
| Proiect | Status |
|---------|--------|
| ElectroGestion | Activ |
| BFC Marketplace | Activ |
| Amazon FBA | Activ |

## Scurtaturi Claude
- Ctrl+Shift+C = Chat Claude
- Ctrl+Shift+A = Intreaba despre selectie
- Ctrl+Shift+S = Rezuma nota
'@ | Set-Content "$VaultPath\00-Dashboard\Home.md" -Encoding UTF8

@'
# ElectroGestion
## Foldere
- Projects/ - Proiecte active
- Meetings/ - Intalniri
- Tasks/ - Task-uri
- Reports/ - Rapoarte
'@ | Set-Content "$VaultPath\01-ElectroGestion\_INDEX.md" -Encoding UTF8

@'
# BFC Marketplace
## Foldere
- Products/ - Catalog produse
- Orders/ - Comenzi
- Analytics/ - Rapoarte
- Listings/ - Listinguri
'@ | Set-Content "$VaultPath\02-BFC-Marketplace\_INDEX.md" -Encoding UTF8

@'
# Amazon FBA
## Foldere
- Inventory/ - Stoc FBA
- Listings/ - Listinguri Amazon
- Finances/ - Costuri si profituri
- Reports/ - Rapoarte performanta
'@ | Set-Content "$VaultPath\03-Amazon-FBA\_INDEX.md" -Encoding UTF8

@'
# Nota Zilnica - {{date}}
## Prioritati
- [ ]
- [ ]

## ElectroGestion

## BFC Marketplace

## Amazon FBA

## Note
'@ | Set-Content "$VaultPath\Templates\Daily-Note.md" -Encoding UTF8

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  GATA! Vault creat cu succes." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Urmatori pasi:" -ForegroundColor White
Write-Host "  1. Deschide Obsidian" -ForegroundColor Gray
Write-Host "  2. 'Open folder as vault' -> $VaultPath" -ForegroundColor Gray
Write-Host "  3. Settings -> Community plugins -> Turn off Safe mode -> Enable 'Claude Connector'" -ForegroundColor Gray
Write-Host "  4. Ctrl+Shift+C pentru a deschide Claude" -ForegroundColor Gray
Write-Host ""
Write-Host "Vault path: $VaultPath" -ForegroundColor Yellow
