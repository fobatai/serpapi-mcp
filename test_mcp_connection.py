import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from dotenv import load_dotenv

# Configuratie laden
load_dotenv()
SERPER_KEY = os.getenv("SERPAPI_API_KEY") # We gebruiken deze variabele naam voor de Serper key
BASE_URL = "https://serperremotemcp-waxdvq-4d01cc-18-156-170-236.traefik.me"

if not SERPER_KEY:
    print("❌ FOUT: Geen SERPAPI_API_KEY gevonden in .env")
    exit(1)

# De volledige URL die we willen testen
MCP_URL = f"{BASE_URL}/mcp?api_key={SERPER_KEY}"

async def main():
    print(f"🔄 Verbinden met MCP Server: {MCP_URL} ...")
    
    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialiseren
                await session.initialize()
                print("✅ Verbinding succesvol!")

                # 2. Tools ophalen
                print("\n🔍 Tools ophalen...")
                tools = await session.list_tools()
                
                if not tools:
                    print("⚠️ Geen tools gevonden!")
                else:
                    print(f"✅ {len(tools.tools)} tools gevonden:")
                    for tool in tools.tools:
                        print(f"   - {tool.name}: {tool.description[:50]}...")

                # 3. Test Zoekopdracht (alleen als 'search' tool bestaat)
                search_tool = next((t for t in tools.tools if t.name == "search"), None)
                if search_tool:
                    print("\n🧪 Test 'search' tool uitvoeren (query='apple'வுகளை)...")
                    try:
                        result = await session.call_tool("search", arguments={"q": "apple", "num": 1})
                        print("✅ Zoekresultaat ontvangen!")
                        print(f"   Output preview: {str(result.content)[:200]}...")
                    except Exception as e:
                        print(f"❌ Fout bij uitvoeren van search: {e}")
                else:
                    print("\n⚠️ Tool 'search' niet gevonden, sla test over.")

    except Exception as e:
        print(f"\n❌ KRITIEKE FOUT bij verbinden: {e}")
        print("Mogelijke oorzaken:")
        print("1. Server is down of URL klopt niet.")
        print("2. HTTPS/SSL probleem (certificaat niet geldig).")
        print("3. Authenticatie fout (API sleutel verkeerd).")
        print("4. Pad '/sse' wordt niet goed afgehandeld door server.")

if __name__ == "__main__":
    asyncio.run(main())
