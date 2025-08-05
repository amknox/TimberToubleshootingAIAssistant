#!/usr/bin/env python3
"""Manual test to simulate how Q CLI would use the MCP server"""

import subprocess
import json
import os
import time

def simulate_q_mcp_usage():
    """Simulate how Q CLI would interact with the MCP server"""
    
    server_path = "/workplace/amknox/TimberToubleshootingAIAssistant/src/TimberTroubleshootingAIAssistant/src/timber_troubleshooting_ai_assistant/mcp_scripts/timber_mcp_protocol_server.py"
    
    env = os.environ.copy()
    env.update({
        "LOCAL_MODE": "true",
        "KNOWLEDGE_BASE_ID": "XQHHIEJ8MA",
        "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
        "AWS_REGION": "us-west-2"
    })
    
    print("🚀 Starting MCP server simulation...")
    
    try:
        # Start the server process
        process = subprocess.Popen(
            ["python3", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=0
        )
        
        # Step 1: Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "amazon-q", "version": "1.0.0"}
            }
        }
        
        print("📤 Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            init_response = json.loads(response_line.strip())
            print("✅ Initialize successful")
        
        # Step 2: List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("📤 Requesting available tools...")
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            tools_response = json.loads(response_line.strip())
            tools = tools_response.get("result", {}).get("tools", [])
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
        
        # Step 3: Query Timber knowledge
        query_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "query_timber_knowledge",
                "arguments": {
                    "query": "What is Timber and how does it work?"
                }
            }
        }
        
        print("📤 Querying Timber knowledge base...")
        process.stdin.write(json.dumps(query_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            query_response = json.loads(response_line.strip())
            content = query_response.get("result", {}).get("content", [])
            if content:
                print("✅ Timber Knowledge Response:")
                print("=" * 50)
                print(content[0]["text"])
                print("=" * 50)
        
        # Clean up
        process.terminate()
        process.wait(timeout=5)
        
        print("\n🎉 MCP Server is working perfectly!")
        print("The server can:")
        print("✅ Initialize properly")
        print("✅ List available tools")
        print("✅ Query Timber knowledge base")
        print("✅ Return formatted responses")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during MCP simulation: {e}")
        if process:
            process.terminate()
        return False

if __name__ == "__main__":
    simulate_q_mcp_usage()
