#!/usr/bin/env python3
"""Simple test for MCP server functionality"""

import json
import subprocess
import sys
import os

def test_mcp_server_simple():
    """Test the MCP server with basic functionality"""
    
    server_path = "/workplace/amknox/TimberToubleshootingAIAssistant/src/TimberTroubleshootingAIAssistant/src/timber_troubleshooting_ai_assistant/mcp_scripts/timber_mcp_protocol_server.py"
    
    # Set environment for local testing
    env = os.environ.copy()
    env.update({
        "LOCAL_MODE": "true",
        "KNOWLEDGE_BASE_ID": "XQHHIEJ8MA",
        "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
    })
    
    # Test: Initialize
    print("=== Testing MCP Server Initialization ===")
    init_request = {
        "jsonrpc": "2.0", 
        "id": 1, 
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
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
        
        # Send the request
        input_data = json.dumps(init_request) + "\n"
        stdout, stderr = process.communicate(input=input_data, timeout=15)
        
        print(f"STDOUT: {stdout}")
        if stderr:
            print(f"STDERR: {stderr}")
            
        # Try to parse the response
        if stdout.strip():
            try:
                response = json.loads(stdout.strip())
                print(f"Parsed response: {json.dumps(response, indent=2)}")
            except json.JSONDecodeError:
                print("Response is not valid JSON")
        
    except subprocess.TimeoutExpired:
        print("Test timed out")
        process.kill()
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_mcp_server_simple()
