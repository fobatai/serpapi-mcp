#!/usr/bin/env python3
"""
Debug script om MCP server te testen zonder OpenAI Batch API.
Simuleert exact hoe OpenAI de MCP server aanroept.
"""
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuratie
BASE_URL = "https://serperremotemcp-waxdvq-4d01cc-18-156-170-236.traefik.me"
API_KEY = os.getenv("SERPAPI_API_KEY", "")

def check_version():
    """Check welke versie momenteel gedeployed is."""
    print("=" * 60)
    print("1. VERSION CHECK")
    print("=" * 60)
    try:
        r = httpx.get(f"{BASE_URL}/version", verify=False, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Server versie: {data.get('version', 'unknown')}")
            print(f"   Timestamp: {data.get('timestamp', 'unknown')}")
            print(f"   ASGI Wrapper: {data.get('asgi_wrapper', 'unknown')}")
            return data.get('version')
        else:
            print(f"❌ Onverwachte response: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Fout: {e}")
        return None

def test_mcp_without_accept_header():
    """Test MCP zonder Accept header (zoals OpenAI doet)."""
    print("\n" + "=" * 60)
    print("2. MCP TEST ZONDER ACCEPT HEADER (simuleert OpenAI)")
    print("=" * 60)
    
    url = f"{BASE_URL}/mcp?api_key={API_KEY}"
    body = {
        'jsonrpc': '2.0', 
        'method': 'tools/list', 
        'params': {}, 
        'id': 1
    }
    
    # OpenAI stuurt alleen Content-Type, GEEN Accept header!
    headers = {'Content-Type': 'application/json'}
    
    print(f"URL: {url[:50]}...")
    print(f"Headers: {headers}")
    print(f"Body: {json.dumps(body)}")
    
    try:
        r = httpx.post(url, json=body, verify=False, headers=headers, timeout=15)
        print(f"\nStatus: {r.status_code}")
        
        if r.status_code == 200:
            print("✅ SUCCESS! Server accepteert request zonder Accept header")
            print(f"Response preview: {r.text[:300]}...")
            return True
        elif r.status_code == 406:
            print("❌ FOUT: 406 Not Acceptable - Accept header fix werkt NIET")
            print(f"Response: {r.text}")
            return False
        else:
            print(f"⚠️ Onverwachte status: {r.status_code}")
            print(f"Response: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_mcp_with_accept_header():
    """Test MCP met correcte Accept header (controle test)."""
    print("\n" + "=" * 60)
    print("3. MCP TEST MET ACCEPT HEADER (controle)")
    print("=" * 60)
    
    url = f"{BASE_URL}/mcp?api_key={API_KEY}"
    body = {
        'jsonrpc': '2.0', 
        'method': 'tools/list', 
        'params': {}, 
        'id': 1
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    try:
        r = httpx.post(url, json=body, verify=False, headers=headers, timeout=15)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            print("✅ SUCCESS met Accept header")
            return True
        else:
            print(f"❌ FOUT: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_tool_call():
    """Test een echte tool call."""
    print("\n" + "=" * 60)
    print("4. TOOL CALL TEST (search)")
    print("=" * 60)
    
    url = f"{BASE_URL}/mcp?api_key={API_KEY}"
    body = {
        'jsonrpc': '2.0', 
        'method': 'tools/call', 
        'params': {
            'name': 'search',
            'arguments': {'q': 'test', 'num': 1}
        }, 
        'id': 2
    }
    
    headers = {'Content-Type': 'application/json'}  # Geen Accept header!
    
    try:
        r = httpx.post(url, json=body, verify=False, headers=headers, timeout=30)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            print("✅ Tool call succesvol!")
            print(f"Response preview: {r.text[:400]}...")
            return True
        else:
            print(f"❌ FOUT: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("\n🔍 MCP SERVER DEBUG TEST\n")
    
    if not API_KEY:
        print("❌ SERPAPI_API_KEY niet gevonden in .env!")
        return
    
    # 1. Check versie
    version = check_version()
    
    # 2. Test zonder Accept header (dit is wat faalt)
    test1 = test_mcp_without_accept_header()
    
    # 3. Test met Accept header (controle)
    test2 = test_mcp_with_accept_header()
    
    # 4. Test tool call
    test3 = test_tool_call()
    
    # Samenvatting
    print("\n" + "=" * 60)
    print("SAMENVATTING")
    print("=" * 60)
    print(f"Server versie: {version or 'NIET BESCHIKBAAR'}")
    print(f"Test zonder Accept header: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test met Accept header: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Tool call test: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 ALLE TESTS GESLAAGD - Server is klaar voor OpenAI!")
    elif not test1:
        print("\n⚠️ Accept header fix werkt niet - deploy eerst de nieuwe versie!")
    else:
        print("\n⚠️ Sommige tests gefaald - check de output hierboven")

if __name__ == "__main__":
    main()
