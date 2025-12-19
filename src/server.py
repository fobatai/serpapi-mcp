import uvicorn
import os
import json
import httpx
from typing import Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

# Configuratie laden
load_dotenv()

# 1. Maak de FastMCP Server aan
mcp = FastMCP("Serper.dev MCP Server")

# 2. Definieer de Tools
@mcp.tool()
async def search(q: str, type: str = "search", gl: str = "nl", hl: str = "nl", location: Optional[str] = None, num: int = 10) -> str:
    """Search Google using Serper.dev."""
    request = get_http_request()
    api_key = getattr(request.state, "api_key", None)
    
    if not api_key:
        return "Error: No API key available"

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

# 3. Middleware
class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip for healthcheck and root
        if request.url.path in ["/", "/healthcheck"]:
            return await call_next(request)

        api_key = None
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            api_key = auth.split(" ", 1)[1].strip()
        
        if not api_key:
            api_key = request.query_params.get("api_key")
            
        if not api_key:
            api_key = os.getenv("SERPER_API_KEY")

        if not api_key:
            # Als we geen key hebben, maar het is een SSE connectie poging, 
            # willen we misschien een duidelijke error geven
            if request.url.path.endswith("/sse"):
                 return JSONResponse({"error": "Missing API Key"}, status_code=401)
        
        request.state.api_key = api_key
        return await call_next(request)

# 4. Handlers voor extra routes
async def healthcheck(request):
    return JSONResponse({"status": "healthy"})

async def homepage(request):
    # Print routes for debugging
    routes = [str(r) for r in request.app.routes]
    return JSONResponse({
        "service": "Serper MCP",
        "routes": routes,
        "instructions": "Use /sse?api_key=... endpoint"
    })

# 5. Bouw de Starlette App EXPLICIET
def create_app():
    middleware = [
        Middleware(ApiKeyMiddleware),
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
    
    app = Starlette(debug=True, middleware=middleware)
    
    app.add_route("/", homepage, methods=["GET"])
    app.add_route("/healthcheck", healthcheck, methods=["GET"])
    
    # Mount de MCP server op de root
    # Dit voegt /sse en /messages toe
    mcp.mount_http(app, path="/") 
    
    return app

# Entry point voor Uvicorn
starlette_app = create_app()

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(starlette_app, host=host, port=port)