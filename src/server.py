import uvicorn
import os
import json
import httpx
from typing import Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

print("--- SERVER STARTUP SEQUENCE ---")

load_dotenv()

# 1. Maak de FastMCP Server aan
mcp = FastMCP("Serper.dev MCP Server")
print("✅ FastMCP instance created")

# 2. Definieer de Tools
@mcp.tool()
async def search(q: str, type: str = "search", gl: str = "nl", hl: str = "nl", location: Optional[str] = None, num: int = 10) -> str:
    """Search Google using Serper.dev."""
    # Haal de request context op om de API key te vinden
    # In FastAPI/FastMCP mount mode moeten we soms de state anders benaderen
    # We proberen de key uit de omgeving of uit een globale plek te halen
    # (FastMCP dependencies kunnen hier lastig zijn, dus we houden het simpel)
    api_key = os.getenv("CURRENT_API_KEY") # Tijdelijke hack voor relay
    
    if not api_key:
        return "Error: No API key available on server. Make sure to provide it."

    url = f"https://google.serper.dev/{type}"
    payload = {"q": q, "gl": gl, "hl": hl, "num": num}
    if location:
        payload["location"] = location

    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error connecting to Serper.dev: {str(e)}"

@mcp.tool()
async def visit_page(url: str) -> str:
    """Visit a webpage via Jina AI."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jina_url, headers=headers, timeout=60.0)
            return response.text
        except Exception as e:
            return f"Error visiting page: {str(e)}"

# 3. Bouw de FastAPI App
app = FastAPI(title="Serper Relay MCP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    print("DEBUG: Root endpoint hit")
    return {
        "status": "online",
        "service": "Serper MCP Relay",
        "endpoints": ["/mcp", "/healthcheck"]
    }

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# De 'magic' koppeling voor de relay
@app.get("/mcp")
@app.post("/mcp")
async def mcp_relay(request: Request):
    print(f"DEBUG: MCP Relay hit: {request.method} {request.url.path}")
    
    # Haal API key op
    api_key = request.query_params.get("api_key")
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        api_key = auth.split(" ", 1)[1].strip()
    
    if not api_key:
        api_key = os.getenv("SERPER_API_KEY")
        
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key. Use ?api_key=...")

    # Sla de key op in een environment variabele (niet thread-safe, maar voor deze batch ok)
    # Een betere manier is request state, maar FastMCP tools hebben hun eigen scope.
    os.environ["CURRENT_API_KEY"] = api_key
    
    # Gebruik de interne FastMCP handler
    # We moeten de request path aanpassen zodat FastMCP denkt dat het een directe aanroep is
    # FastMCP mount zichzelf meestal op de root van de sub-app
    return await mcp.handle_sse(request) if request.method == "GET" else await mcp.handle_post(request)

# Mount FastMCP op de app (dit regelt de tools/resources endpoints)
# We mounten hem op een subpad om conflicten te voorkomen
mcp.mount(app)
print("✅ FastMCP mounted on app")

if __name__ == "__main__":
    print("🚀 Starting Uvicorn...")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)