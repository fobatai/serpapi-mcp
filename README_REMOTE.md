# SerpApi Remote MCP Server Gebruikershandleiding

Deze server draait op `http://serper-mcp.pontifexxpaddock.com/` en fungeert als een beveiligde relay voor de SerpApi MCP-service.

## Beveiligingsmodel (Relay)

De server slaat zelf geen API-sleutels op. Om de server te gebruiken, moet je je eigen **SerpApi API Key** meesturen bij elk verzoek. Dit zorgt ervoor dat:
- Jouw eigen SerpApi-tegoed wordt gebruikt.
- Alleen mensen met een geldige sleutel de server kunnen gebruiken.

---

## Configuratie in Claude Desktop

Om deze remote server te gebruiken in Claude Desktop, voeg je de volgende configuratie toe aan je `claude_desktop_config.json`:

### macOS
Pad: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Windows
Pad: `%APPDATA%\Claude\claude_desktop_config.json`

### De Configuratie

Vervang `JOUW_API_KEY_HIER` door je eigen API-sleutel van [SerpApi.com](https://serpapi.com/).

```json
{
  "mcpServers": {
    "serpapi-remote": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sse",
        "http://serper-mcp.pontifexxpaddock.com/JOUW_API_KEY_HIER/mcp"
      ]
    }
  }
}
```

---

## Geavanceerd gebruik

De server ondersteunt twee manieren om de API-sleutel te ontvangen:

1. **Via de URL (Aanbevolen voor MCP/SSE clients):**
   `http://serper-mcp.pontifexxpaddock.com/{JOUW_API_KEY}/mcp`

2. **Via HTTP Headers:**
   Voeg een header toe aan je verzoek:
   `Authorization: Bearer JOUW_API_KEY`

---

## Tools Beschikbaar

Zodra verbonden, heb je toegang tot de volgende tool:

### `search`
Een universele tool die alle SerpApi engines ondersteunt (Google, Bing, DuckDuckGo, etc.).

**Parameters:**
- `params`: Een dictionary met zoekparameters (bijv. `{"q": "koffie amsterdam", "engine": "google"}`)
- `mode`: `"complete"` (standaard) of `"compact"` (voor minder dataverbruik).

---

## Status controleren
Je kunt altijd de status van de server controleren via:
http://serper-mcp.pontifexxpaddock.com/healthcheck
