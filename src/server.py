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

# Version for deployment tracking - increment this with each deployment
SERVER_VERSION = "1.0.5"

# 1. Maak de FastMCP Server aan
mcp = FastMCP("Serper.dev MCP Server")

# 2. Definieer de Tools
@mcp.tool()
async def search(query: str) -> str:
    """Search Google using Serper.dev. Returns search results for the given query."""
    request = get_http_request()
    api_key = getattr(request.state, "api_key", None)
    
    if not api_key:
        return "Error: No API key available"

    url = "https://google.serper.dev/search"
    payload = {"q": query, "gl": "nl", "hl": "nl", "num": 10}

    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error connecting to Serper.dev: {str(e)}"

@mcp.tool()
async def fetch(url: str) -> str:
    """Fetch content from a webpage via Jina AI."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jina_url, headers=headers, timeout=60.0)
            return response.text
        except Exception as e:
            return f"Error fetching page: {str(e)}"

# 3. Middleware
class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip for healthcheck and root
        if request.url.path in ["/", "/healthcheck", "/version"]:
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

# 4. Handlers
async def healthcheck_handler(request):
    return JSONResponse({"status": "healthy", "version": SERVER_VERSION})

async def version_handler(request):
    return JSONResponse({
        "version": SERVER_VERSION,
        "timestamp": datetime.now().isoformat(),
        "asgi_wrapper": "AcceptHeaderASGIWrapper",
        "stateless_http": True
    })

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
        "version": SERVER_VERSION,
        "debug_routes": routes_info
    })

def main():
    middleware = [
        Middleware(ApiKeyMiddleware),
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
    
    # Gebruik de native FastMCP http app builder
    starlette_app = mcp.http_app(middleware=middleware, stateless_http=True)
    
    # Overschrijf/Voeg toe onze eigen routes
    starlette_app.add_route("/", root_handler, methods=["GET"])
    starlette_app.add_route("/healthcheck", healthcheck_handler, methods=["GET"])
    starlette_app.add_route("/version", version_handler, methods=["GET"])
    
    # ASGI Wrapper: Inject Accept header at the lowest level before FastMCP processes it
    # This is needed because OpenAI's Batch API doesn't send the required Accept header
    class AcceptHeaderASGIWrapper:
        def __init__(self, app):
            self.app = app
        
        async def __call__(self, scope, receive, send):
            if scope["type"] == "http" and scope.get("path") == "/mcp":
                # Check if Accept header is missing or incomplete
                headers = list(scope.get("headers", []))
                accept_present = False
                accept_value = b""
                
                for i, (name, value) in enumerate(headers):
                    if name.lower() == b"accept":
                        accept_present = True
                        accept_value = value
                        break
                
                # If Accept header is missing or doesn't contain both required types
                needs_injection = not accept_present or (
                    b"application/json" not in accept_value or 
                    b"text/event-stream" not in accept_value
                )
                
                if needs_injection:
                    # Remove existing Accept header if present
                    headers = [(n, v) for n, v in headers if n.lower() != b"accept"]
                    # Add the required Accept header
                    headers.append((b"accept", b"application/json, text/event-stream"))
                    scope = dict(scope)
                    scope["headers"] = headers
            
            await self.app(scope, receive, send)
    
    # Wrap the Starlette app with our ASGI wrapper
    wrapped_app = AcceptHeaderASGIWrapper(starlette_app)
    
    print("🚀 Starting Uvicorn (Starlette with ASGI wrapper)...")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(wrapped_app, host=host, port=port, ws="none")

if __name__ == "__main__":
    main()
