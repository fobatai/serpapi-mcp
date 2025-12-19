import uvicorn
import time
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, HTMLResponse
from starlette.requests import Request
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from dotenv import load_dotenv
import os
import json
from typing import Any, Optional
import httpx
import logging
from datetime import datetime

load_dotenv()

mcp = FastMCP("Serper.dev MCP Server")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/healthcheck" or request.url.path == "/":
            return await call_next(request)

        api_key = None
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            api_key = auth.split(" ", 1)[1].strip()

        original_path = request.scope.get("path", "")
        path_parts = original_path.strip("/").split("/") if original_path else []

        if not api_key and len(path_parts) >= 2 and path_parts[1] == "mcp":
            api_key = path_parts[0]
            # No path rewriting here anymore. We handle this via explicit route proxying.

        if not api_key:
            api_key = os.getenv("SERPER_API_KEY")

        if not api_key:
            # If we are in the proxy route, the key might not be extracted yet by middleware logic
            # but will be captured by the route handler. So we allow passing if path matches pattern.
            if len(path_parts) >= 2 and path_parts[1] == "mcp":
                 return await call_next(request)

            return JSONResponse(
                {"error": "Missing Serper API key. Provide it in the Authorization header or via path /{API_KEY}/mcp"},
                status_code=401,
            )

        request.state.api_key = api_key
        return await call_next(request)

@mcp.tool()
async def search(q: str, type: str = "search", gl: str = "nl", hl: str = "nl", location: Optional[str] = None, num: int = 10) -> str:
    """Search Google using Serper.dev.
    
    Args:
        q: The search query
        type: Search type ('search', 'images', 'news', 'places', 'shopping')
        gl: Country code (default: nl)
        hl: Language code (default: nl)
        location: Specific location (e.g. 'Amsterdam, Netherlands')
        num: Number of results (default: 10)
    """
    request = get_http_request()
    api_key = getattr(request.state, "api_key", None)
    
    if not api_key:
        return "Error: No API key available"

    url = f"https://google.serper.dev/{type}"
    payload = {
        "q": q,
        "gl": gl,
        "hl": hl,
        "num": num
    }
    if location:
        payload["location"] = location

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return f"Error from Serper.dev ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Error connecting to Serper.dev: {str(e)}"

@mcp.tool()
async def visit_page(url: str) -> str:
    """Visit a webpage and extract its content as clean Markdown text.
    
    Use this tool to read the full content of a search result to find specific details 
    like technical specifications, EOL status, or replacement parts.
    
    Args:
        url: The full URL of the webpage to visit.
    """
    jina_url = f"https://r.jina.ai/{url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient() as client:
        try:
            # Increased timeout for page scraping
            response = await client.get(jina_url, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Error visiting page: {str(e)}"

async def healthcheck_handler(request):
    return JSONResponse({
        "status": "healthy",
        "service": "Serper.dev MCP Server",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

async def root_handler(request):
    routes = [f"{type(r).__name__}: {r.path}" for r in request.app.routes if hasattr(r, 'path')]
    # Also include Mounts
    for r in request.app.routes:
        if not hasattr(r, 'path'):
            routes.append(str(r))
            
    return JSONResponse({
        "status": "online", 
        "service": "Serper.dev MCP Server",
        "debug_routes": routes
    })

async def proxy_sse(request):
    """
    Proxy request from /{api_key}/mcp to the internal /sse endpoint.
    """
    print(f"DEBUG: Proxy hit for {request.url.path}")
    api_key = request.path_params.get("api_key")
    if api_key:
        request.state.api_key = api_key
    
    # Find the SSE route by checking the endpoint name or path
    for route in request.app.routes:
        if hasattr(route, "path") and route.path == "/sse":
            print("DEBUG: Found /sse route, forwarding...")
            return await route.endpoint(request)
        # Soms heet de functie 'handle_sse'
        if hasattr(route, "endpoint") and getattr(route.endpoint, "__name__", "") == "handle_sse":
             print("DEBUG: Found handle_sse endpoint, forwarding...")
             return await route.endpoint(request)
            
    print("DEBUG: SSE route NOT found!")
    return JSONResponse({"error": "Internal SSE endpoint not found", "routes": [str(r) for r in request.app.routes]}, status_code=500)

def main():
    middleware = [
        Middleware(ApiKeyMiddleware),
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
    starlette_app = mcp.http_app(middleware=middleware, stateless_http=True, json_response=True)
    
    starlette_app.add_route("/", root_handler, methods=["GET"])
    starlette_app.add_route("/healthcheck", healthcheck_handler, methods=["GET"])
    starlette_app.add_route("/{api_key}/mcp", proxy_sse, methods=["GET"])
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(starlette_app, host=host, port=port, ws="none")

if __name__ == "__main__":
    main()