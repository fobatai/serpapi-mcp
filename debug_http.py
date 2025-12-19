import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
SERPER_KEY = os.getenv("SERPAPI_API_KEY")
BASE_URL = "https://serperremotemcp-waxdvq-4d01cc-18-156-170-236.traefik.me"
FULL_URL = f"{BASE_URL}/mcp?api_key={SERPER_KEY}"

async def debug_connection():
    print(f"🔍 Testen van URL: {FULL_URL}")
    
    async with httpx.AsyncClient(verify=False) as client: # Verify=False om SSL errors even uit te sluiten
        try:
            # 1. Probeer een simpele GET request naar de ROOT om routes te zien
            print("\n--- Stap 0: Check Routes op / ---")
            root_resp = await client.get(BASE_URL + "/")
            print(f"Root Status: {root_resp.status_code}")
            print(f"Root Body: {root_resp.text}")

            # 2. Probeer een simpele GET request naar MCP endpoint
            print("\n--- Stap 1: GET Request naar MCP ---")
            headers = {"Accept": "text/event-stream"}
            response = await client.get(FULL_URL, headers=headers, follow_redirects=False)
            
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Content Preview: {response.text[:200]}")
            
            if response.status_code in [301, 302, 307, 308]:
                print(f"👉 Redirect naar: {response.headers.get('location')}")
                
            # 2. Als redirect, volg hem dan handmatig om te zien waar we uitkomen
            if response.status_code in [301, 302, 307, 308]:
                print("\n--- Stap 2: Volg Redirect ---")
                redirect_url = response.headers.get('location')
                if redirect_url.startswith("/"):
                    redirect_url = BASE_URL + redirect_url
                
                print(f"Volgen naar: {redirect_url}")
                resp2 = await client.get(redirect_url)
                print(f"Status Code: {resp2.status_code}")
                print(f"Content-Type: {resp2.headers.get('content-type')}")
                
        except Exception as e:
            print(f"❌ Exception tijdens request: {e}")

if __name__ == "__main__":
    asyncio.run(debug_connection())
