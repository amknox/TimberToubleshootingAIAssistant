#!/usr/bin/env python3
"""Test script for the Timber MCP server"""

import json
import subprocess
import sys

def test_mcp_server():
    """Test the MCP server with various requests"""
    
    server_path = "/workplace/amknox/TimberToubleshootingAIAssistant/src/TimberTroubleshootingAIAssistant/src/timber_troubleshooting_ai_assistant/mcp_scripts/timber_mcp_server_enhanced.py"
    
    env = {
        "LOCAL_MODE": "false",
        "KNOWLEDGE_BASE_ID": "XQHHIEJ8MA",
        "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
    }
    
    # Test 1: Initialize
    print("=== Test 1: Initialize ===")
    init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    
    try:
        process = subprocess.Popen(
            ["python3", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**env}
        )
        
        stdout, stderr = process.communicate(input=json.dumps(init_request) + "\n", timeout=10)
        print(f"Response: {stdout.strip()}")
        if stderr:
            print(f"Stderr: {stderr}")
            
    except subprocess.TimeoutExpired:
        print("Initialize test timed out")
        process.kill()
    except Exception as e:
        print(f"Initialize test failed: {e}")
    
    # Test 2: List tools
    print("\n=== Test 2: List Tools ===")
    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    
    try:
        process = subprocess.Popen(
            ["python3", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**env}
        )
        
        stdout, stderr = process.communicate(input=json.dumps(tools_request) + "\n", timeout=10)
        print(f"Response: {stdout.strip()}")
        if stderr:
            print(f"Stderr: {stderr}")
            
    except subprocess.TimeoutExpired:
        print("Tools list test timed out")
        process.kill()
    except Exception as e:
        print(f"Tools list test failed: {e}")
    
    # Test 3: Query knowledge base
    print("\n=== Test 3: Query Knowledge Base ===")
    query_request = {
        "jsonrpc": "2.0", 
        "id": 3, 
        "method": "tools/call", 
        "params": {
            "name": "query_timber_knowledge",
            "arguments": {
                "query": "What is timber and how do I troubleshoot timber issues?"
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
            env={**env}
        )
        
        stdout, stderr = process.communicate(input=json.dumps(query_request) + "\n", timeout=30)
        print(f"Response: {stdout.strip()}")
        if stderr:
            print(f"Stderr: {stderr}")
            
    except subprocess.TimeoutExpired:
        print("Query test timed out")
        process.kill()
    except Exception as e:
        print(f"Query test failed: {e}")

if __name__ == "__main__":
    test_mcp_server()
