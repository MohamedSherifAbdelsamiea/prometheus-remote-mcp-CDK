#!/usr/bin/env python3
"""
Test Lambda MCP endpoint with proper authentication
"""

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import requests
import json

def get_token():
    response = requests.post(
        "https://prometheus-mcp-si618c.auth.us-west-2.amazoncognito.com/oauth2/token",
        data={'grant_type': 'client_credentials', 'scope': 'prometheus-mcp-server/read prometheus-mcp-server/write'},
        auth=("1krhi8ratf7605nt06aq7oo7hc", "nobaos6quoaemlvu3qrvvnltnscgi1ihep61cnkarbcr9j5k54u"),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']

def create_transport(mcp_url, token):
    return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {token}"})

def test_direct_http():
    """Test direct HTTP call to Lambda MCP endpoint"""
    token = get_token()
    url = "https://0ixu8aqtkc.execute-api.us-west-2.amazonaws.com/prod/mcp"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    
    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

def run_agent():
    token = get_token()
    print("✅ Authenticated")
    
    # Test direct HTTP first
    if not test_direct_http():
        print("❌ Direct HTTP test failed")
        return
    
    print("✅ Direct HTTP test passed")
    
    # Use the new Lambda MCP endpoint
    mcp_url = "https://0ixu8aqtkc.execute-api.us-west-2.amazonaws.com/prod/mcp"
    
    model = BedrockModel(inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0", streaming=True)
    mcp_client = MCPClient(lambda: create_transport(mcp_url, token))
    
    try:
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(model=model, tools=tools)
            print(f"✅ Agent ready with {len(tools)} MCP tools")
            
            while True:
                query = input("\n🔍 Query: ").strip()
                if query.lower() in ['quit', 'q']: break
                if not query: continue
                
                try:
                    response = agent(query)
                    content = response.message.get('content', '') if hasattr(response, 'message') and response.message else response
                    
                    if isinstance(content, list):
                        for item in content:
                            if item.get('type') == 'text':
                                print(f"🤖 {item.get('text', '')}")
                    else:
                        print(f"🤖 {content}")
                except Exception as e:
                    print(f"❌ {e}")
    except Exception as e:
        print(f"❌ MCP Client failed: {e}")

if __name__ == "__main__":
    run_agent()
