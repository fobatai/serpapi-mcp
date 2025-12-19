# Serper.dev MCP Server (Relay)

Dit is een Model Context Protocol (MCP) server die fungeert als een 'stateless relay' voor de [Serper.dev](https://serper.dev) API. 

Deze server stelt LLM's (zoals Claude via Claude Desktop of OpenAI via scripts) in staat om realtime Google zoekresultaten (web, afbeeldingen, nieuws, shopping) op te halen. De server is geoptimaliseerd voor Nederlandse resultaten (`gl=nl`, `hl=nl`).

## 🚀 Hoe het werkt

De server draait als een tussenschakel. Je stuurt je eigen Serper.dev API-sleutel mee in het verzoek (via de URL of header). De server gebruikt die sleutel om de zoekopdracht uit te voeren bij Serper.dev en stuurt het resultaat terug naar de LLM.

**Endpoint:** `https://serper-mcp.pontifexxpaddock.com/`

## 🛠️ Gebruik in Claude Desktop

Om deze server te gebruiken in de Claude Desktop app, voeg je de volgende configuratie toe aan je config bestand.

**Locatie Config bestand:**
*   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
*   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Configuratie:**
Vervang `JOUW_SERPER_KEY` door je sleutel van [serper.dev](https://serper.dev).

```json
{
  "mcpServers": {
    "serper-nl": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sse",
        "https://serper-mcp.pontifexxpaddock.com/sse?api_key=JOUW_SERPER_KEY"
      ]
    }
  }
}
```

## 🐍 Gebruik in Python Scripts (OpenAI)

Je kunt deze MCP server ook gebruiken als 'tool' in je eigen OpenAI scripts (bijvoorbeeld voor Deep Research of Batch processing).

**Voorbeeld Tool Definitie:**

```python
MCP_SERVER_URL = "https://serper-mcp.pontifexxpaddock.com/sse?api_key=JOUW_SERPER_KEY"

tools = [
    {
        "type": "mcp",
        "server_label": "serper_nl",
        "server_url": MCP_SERVER_URL,
        "require_approval": "never"
    }
]
```

## 📦 Deployment (Dokploy / Docker)

Deze repository is klaar voor deployment op platforms zoals Dokploy, Railway of elke Docker host.

### Environment Variables
De server heeft **geen** API-sleutels nodig in de environment variables, omdat deze door de client worden aangeleverd.

*   `MCP_HOST`: `0.0.0.0` (Standaard)
*   `MCP_PORT`: `8000` (Standaard)

### Start Commando
De server wordt gestart via de `Procfile`:
```bash
web: python src/server.py
```

## 📡 API Endpoints

*   `GET /` - Informatiepagina met instructies.
*   `GET /healthcheck` - Controleert de status van de server.
*   `GET /sse?api_key=...` - SSE Endpoint voor MCP clients.

## 📄 Licentie
MIT