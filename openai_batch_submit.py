import pandas as pd
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

# --- CONFIGURATIE ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Geen OPENAI_API_KEY gevonden in .env bestand!")
if not SERPAPI_API_KEY:
    raise ValueError("Geen SERPAPI_API_KEY gevonden! Deze is nodig voor de Remote MCP URL.")

MODEL_NAAM = "o4-mini-deep-research-2025-06-26"
BESTANDSNAAM = "excel.xlsx"
JSONL_BESTAND = "batch_input_mcp_research.jsonl"

# Remote MCP Configuratie
MCP_SERVER_URL = f"https://serperremotemcp-waxdvq-4d01cc-18-156-170-236.traefik.me/sse?api_key={SERPAPI_API_KEY}"

client = OpenAI(api_key=OPENAI_API_KEY)

def clean_text(text):
    if pd.isna(text): return ""
    return "".join([c if c.isalnum() else " " for c in str(text)]).strip()

def main():
    print(f"1. Excel inlezen: {BESTANDSNAAM}...")
    try:
        df = pd.read_excel(BESTANDSNAAM)
    except FileNotFoundError:
        print(f"Bestand '{BESTANDSNAAM}' niet gevonden!")
        return

    # Voor de test pakken we even 20 items om te zien of de MCP relay goed werkt
    if len(df) > 20:
        df_to_process = df.sample(n=20, random_state=42) 
        print(f"Testmodus: 20 items geselecteerd uit {len(df)} regels.")
    else:
        df_to_process = df
    
    print(f"Bezig met genereren van batch bestand met Remote MCP: {MCP_SERVER_URL}")
    
    with open(JSONL_BESTAND, 'w', encoding='utf-8') as f:
        for index, row in df_to_process.iterrows():
            art_nr = str(row.get('Artikelnummer', ''))
            omschrijving = str(row.get('Omschrijving', ''))
            groep = str(row.get('Artikel_Groep', ''))
            
            veilige_id = clean_text(art_nr).replace(" ", "_")
            custom_id = f"{veilige_id}_{index}" 
            
            prompt_text = f"""
            You are a Senior Procurement Analyst. Research and validate this article using the provided search tool.
            
            Article: {art_nr}
            Description: {omschrijving}
            Group: {groep}

            Verify:
            1. Official Manufacturer
            2. EAN/GTIN
            3. Market Price (EUR)
            4. Lifecycle Status (Active/EOL)
            5. Successor if EOL
            
            CRITICAL INSTRUCTION:
            Use the 'visit_page' tool to inspect search results and verify details on official websites. Do not rely solely on search snippets.

            OUTPUT FORMAT:
            Provide your report and then the results in JSON format within <json> tags.
            """

            request_body = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses", 
                "body": {
                    "model": MODEL_NAAM,
                    "input": prompt_text,
                    "tools": [
                        {
                            "type": "mcp",
                            "server_label": "serper_mcp",
                            "server_url": MCP_SERVER_URL,
                            "require_approval": "never"
                        }
                    ],
                    "max_tool_calls": 20
                }
            }
            f.write(json.dumps(request_body) + "\n")

    print(f"2. Uploaden naar OpenAI ({JSONL_BESTAND})...")
    batch_file = client.files.create(
        file=open(JSONL_BESTAND, "rb"),
        purpose="batch"
    )
    
    print(f"3. Batch starten (File ID: {batch_file.id})...")
    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
        metadata={"description": f"MCP Remote Relay Test - {len(df_to_process)} items"}
    )

    print("-" * 40)
    print(f"BATCH ID: {batch_job.id}")
    print("-" * 40)
    
    with open("batch_id_deep.txt", "w") as f:
        f.write(batch_job.id)

if __name__ == "__main__":
    main()
