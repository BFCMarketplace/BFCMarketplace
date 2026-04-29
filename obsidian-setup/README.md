# Obsidian Vault — ElectroGestion / BFC Marketplace / Amazon FBA

## Setup Rapid (Windows)

```powershell
# 1. Deschide PowerShell ca Administrator
# 2. Naviga la folderul cu fisierele descarcate
cd "C:\path\catre\obsidian-setup"

# 3. Ruleaza scriptul (va intreba de API key)
powershell -ExecutionPolicy Bypass -File setup.ps1

# SAU cu API key direct (nu recomandat in producție):
# powershell -ExecutionPolicy Bypass -File setup.ps1 -AnthropicApiKey "sk-ant-..."
```

## Structura Vault

```
ObsidianVault/
├── 00-Dashboard/          # Pagina principala cu KPIs
├── 01-ElectroGestion/     # Gestiune echipamente electrice
│   ├── Projects/
│   ├── Meetings/
│   ├── Tasks/
│   └── Reports/
├── 02-BFC-Marketplace/    # Platforma e-commerce
│   ├── Products/
│   ├── Orders/
│   ├── Analytics/
│   └── Listings/
├── 03-Amazon-FBA/         # Operatiuni FBA
│   ├── Inventory/
│   ├── Listings/
│   ├── Finances/
│   └── Reports/
├── Templates/             # Template-uri reutilizabile
└── Archive/               # Note arhivate
```

## Scurtaturi Claude Connector

| Shortcut | Actiune |
|----------|---------|
| `Ctrl+Shift+C` | Deschide chat Claude |
| `Ctrl+Shift+A` | Intreaba Claude despre selectie |
| `Ctrl+Shift+S` | Rezuma nota curenta |
| `Ctrl+P` → `Claude: Comuta` | Schimba proiectul activ |

## Token Optimization

Plugin-ul foloseste **Anthropic Prompt Caching** care reduce costul system prompt-ului cu ~90%:
- System prompt-urile per proiect sunt cache-uite server-side
- Istoricul conversatiei este trunchiat automat (configureaza in Settings)
- Statusbar arata proiectul activ si statistici tokeni

## Securitate

- **NU** include API key-ul in fisiere Git
- Cheia este stocata in `.obsidian/plugins/claude-connector/data.json` (local only)
- Roteste cheia periodic din [console.anthropic.com](https://console.anthropic.com/settings/keys)
