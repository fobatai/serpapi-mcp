import uvicorn
import os
import json
import httpx
from typing import Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, HTMLResponse

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

print("--- SERVER STARTUP (Starlette Mode) ---")

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
        
        # KEY CHANGE: Check query parameters
        if not api_key:
            api_key = request.query_params.get("api_key")
            
        if not api_key:
            api_key = os.getenv("SERPER_API_KEY")

        if not api_key:
            return JSONResponse(
                {"error": "Missing Serper API key. Provide it in the Authorization header or via query param ?api_key=..."},
                status_code=401,
            )
        
        request.state.api_key = api_key
        return await call_next(request)

# OpenAI Batch API Fix: Inject Accept header for MCP endpoint
# OpenAI doesn't send Accept header, causing FastMCP to return 406
class AcceptHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/mcp":
            # Create new scope with injected Accept header
            scope = dict(request.scope)
            headers = [(k, v) for k, v in request.headers.raw]
            
            # Check if Accept header is missing or doesn't include required types
            accept_header = request.headers.get("accept", "")
            if "application/json" not in accept_header or "text/event-stream" not in accept_header:
                # Remove existing Accept header if present
                headers = [(k, v) for k, v in headers if k.lower() != b"accept"]
                # Add the required Accept header
                headers.append((b"accept", b"application/json, text/event-stream"))
                scope["headers"] = headers
                
                from starlette.requests import Request
                request = Request(scope, request.receive)
        
        return await call_next(request)

# 4. Handlers
async def healthcheck_handler(request):
    return JSONResponse({"status": "healthy"})

async def root_handler(request):
    # Print routes for debugging, robust against missing attributes
    routes_info = []
    for route in request.app.routes:
        try:
            info = {"type": type(route).__name__}
            if hasattr(route, "path"):
                info["path"] = route.path
            if hasattr(route, "methods") and route.methods:
                info["methods"] = list(route.methods)
            routes_info.append(info)
        except Exception as e:
            routes_info.append({"error": str(e), "repr": str(route)})
            
    return JSONResponse({
        "status": "online", 
        "service": "Serper.dev MCP Server",
        "debug_routes": routes_info
    })

def main():
    middleware = [
        Middleware(AcceptHeaderMiddleware),  # Must be first to inject Accept header before other processing
        Middleware(ApiKeyMiddleware),
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
    
    # Gebruik de native FastMCP http app builder
    # json_response=True verwijderd voor OpenAI Batch API compatibiliteit
    # OpenAI stuurt geen Accept: application/json header, wat 406 errors veroorzaakte
    starlette_app = mcp.http_app(middleware=middleware, stateless_http=True)
    
    # Overschrijf/Voeg toe onze eigen routes
    starlette_app.add_route("/", root_handler, methods=["GET"])
    starlette_app.add_route("/healthcheck", healthcheck_handler, methods=["GET"])
    
    print("🚀 Starting Uvicorn (Starlette)...")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(starlette_app, host=host, port=port, ws="none")

if __name__ == "__main__":
    main()