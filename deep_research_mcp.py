import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# --- CONFIGURATIE ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Geen OPENAI_API_KEY gevonden in .env bestand!")
if not SERPAPI_API_KEY:
    raise ValueError("Geen SERPAPI_API_KEY gevonden in .env bestand! Deze is nodig voor de remote MCP URL.")

# Gebruik exact hetzelfde model als in je batch scripts
MODEL_NAAM = "o4-mini-deep-research-2025-06-26"

# Het domein van jouw MCP server
MCP_BASE_URL = "http://serper-mcp.pontifexxpaddock.com"
# De volledige URL inclusief de sleutel voor de relay
MCP_SERVER_URL = f"{MCP_BASE_URL}/{SERPAPI_API_KEY}/mcp"

client = OpenAI(api_key=OPENAI_API_KEY)

def main():
    print(f"Start Deep Research met model: {MODEL_NAAM}")
    print(f"Remote MCP URL: {MCP_SERVER_URL}")
    
    # Voorbeeld instructies gebaseerd op je eerdere scripts
    instructions = """
    Je bent een Senior Procurement Analyst. Je taak is om marktdata te valideren voor technische componenten.
    Gebruik de 'search' tool van de MCP server om fabrikanten, prijzen, EAN codes en lifecycle status te verifiëren.
    Citeer je bronnen duidelijk.
    """

    # Input (je kunt dit aanpassen naar een vraag uit je Excel)
    user_input = "Research de huidige marktprijs en beschikbaarheid van de 'Siemens 6ES7214-1AG40-0XB0' PLC. Wat zijn de opvolgers als deze EOL is?"

    try:
        print(f"Aanvraag versturen naar OpenAI ({MODEL_NAAM})...")
        resp = client.responses.create(
            model=MODEL_NAAM,
            background=True,
            reasoning={
                "summary": "auto",
            },
            tools=[
                {
                    "type": "mcp",
                    "server_label": "serpapi_mcp_server",
                    "server_url": MCP_SERVER_URL,
                    "require_approval": "never",
                },
            ],
            instructions=instructions,
            input=user_input,
        )

        print("\n--- RESULTAAT ---")
        if hasattr(resp, 'output_text'):
            print(resp.output_text)
        else:
            print("Geen directe output_text gevonden. Response object:")
            print(resp)

    except Exception as e:
        print(f"Er is een fout opgetreden: {e}")

if __name__ == "__main__":
    main()
