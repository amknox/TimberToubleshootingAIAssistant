#!/usr/bin/env python3
"""Test script to verify MCP server is working with Q CLI"""

import subprocess
import json
import os
import time

def test_mcp_server_standalone():
    """Test the MCP server directly"""
    print("=== Testing MCP Server Directly ===")
    
    server_path = "/workplace/amknox/TimberToubleshootingAIAssistant/src/TimberTroubleshootingAIAssistant/src/timber_troubleshooting_ai_assistant/mcp_scripts/timber_mcp_protocol_server.py"
    
    env = os.environ.copy()
    env.update({
        "LOCAL_MODE": "true",
        "KNOWLEDGE_BASE_ID": "XQHHIEJ8MA",
        "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
    })
    
    # Test query
    query_request = {
        "jsonrpc": "2.0", 
        "id": 1, 
        "method": "tools/call", 
        "params": {
            "name": "query_timber_knowledge",
            "arguments": {
                "query": "What is Timber?"
            }
        }
    }
    
    try:
        process = subprocess.Popen(
            ["python3", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        input_data = json.dumps(query_request) + "\n"
        stdout, stderr = process.communicate(input=input_data, timeout=10)
        
        if stdout.strip():
            response = json.loads(stdout.strip())
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"][0]["text"]
                print("✅ MCP Server Response:")
                print(content)
                return True
            else:
                print("❌ Unexpected response format")
                print(json.dumps(response, indent=2))
        
    except Exception as e:
        print(f"❌ MCP Server test failed: {e}")
        if stderr:
            print(f"Server logs: {stderr}")
    
    return False

def check_mcp_config():
    """Check MCP configuration"""
    print("\n=== Checking MCP Configuration ===")
    
    config_path = "/workplace/amknox/TimberToubleshootingAIAssistant/.amazonq/mcp.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("✅ MCP configuration found:")
        print(json.dumps(config, indent=2))
        
        # Check if server file exists
        server_path = config["mcpServers"]["timber-mcp-server"]["args"][0]
        if os.path.exists(server_path):
            print(f"✅ MCP server file exists: {server_path}")
        else:
            print(f"❌ MCP server file not found: {server_path}")
            
        return True
        
    except Exception as e:
        print(f"❌ MCP configuration error: {e}")
        return False

def main():
    print("🔍 Testing Timber MCP Server Connection\n")
    
    # Test 1: Check MCP configuration
    config_ok = check_mcp_config()
    
    # Test 2: Test MCP server directly
    server_ok = test_mcp_server_standalone()
    
    print("\n=== Summary ===")
    if config_ok and server_ok:
        print("✅ MCP server is working correctly!")
        print("✅ Configuration is valid")
        print("\n🎯 Next steps:")
        print("1. Restart your Q CLI session (exit and run 'q chat' again)")
        print("2. Ask me: 'What is Timber?' and I should use your MCP server")
        print("3. The server is running in LOCAL_MODE with simulated responses")
    else:
        print("❌ Issues found with MCP setup")
        if not config_ok:
            print("- Fix MCP configuration")
        if not server_ok:
            print("- Fix MCP server implementation")

if __name__ == "__main__":
    main()
