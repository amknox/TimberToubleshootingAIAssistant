#!/usr/bin/env python3
"""
Timber Troubleshooting AI Assistant - MCP Protocol Server
Provides JSON-RPC MCP protocol interface for Amazon Q integration
"""

import json
import sys
import os
import logging
import boto3
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/timber_mcp_protocol.log')]
)
logger = logging.getLogger(__name__)

# Environment configuration
LOCAL_MODE = os.environ.get("LOCAL_MODE", "true").lower() == "true"
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "XQHHIEJ8MA")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

# Initialize AWS clients
if not LOCAL_MODE:
    try:
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        bedrock_runtime = boto3.client('bedrock-runtime')
        logger.info(f"Initialized Bedrock clients for KB: {KNOWLEDGE_BASE_ID}")
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock clients: {e}")
        LOCAL_MODE = True


class MCPServer:
    def __init__(self):
        self.tools = {
            "query_timber_kb": {
                "name": "query_timber_kb",
                "description": "Query the Timber knowledge base for troubleshooting information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question or query about Timber"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def query_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Query the Bedrock knowledge base"""
        if LOCAL_MODE:
            return {
                "response": f"[LOCAL MODE] Simulated response for: {query}",
                "source": "local_simulation",
                "confidence": 0.8
            }

        try:
            # Retrieve from knowledge base
            retrieve_response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={'text': query},
                retrievalConfiguration={'vectorSearchConfiguration': {'numberOfResults': 5}}
            )

            retrieved_results = retrieve_response.get('retrievalResults', [])
            if not retrieved_results:
                return {
                    "response": "No relevant information found in the Timber knowledge base.",
                    "source": "knowledge_base",
                    "confidence": 0.0
                }

            # Build context from retrieved results
            context = "\n\n".join([
                f"Document {i+1}: {result['content']['text']}"
                for i, result in enumerate(retrieved_results)
            ])

            # Generate response using Claude
            prompt = f"""Based on the following Timber documentation, answer the user's question: "{query}"

Documentation:
{context}

Please provide a helpful and accurate answer based on the documentation provided."""

            model_response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )

            response_body = json.loads(model_response['body'].read().decode('utf-8'))
            response_text = response_body['content'][0]['text']

            return {
                "response": response_text,
                "source": "knowledge_base",
                "confidence": 0.9,
                "retrieved_count": len(retrieved_results)
            }

        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return {
                "response": f"Error querying knowledge base: {str(e)}",
                "source": "error",
                "confidence": 0.0
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests"""
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "bedrock-kb-retrieval",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": list(self.tools.values())
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "query_timber_kb":
                query = arguments.get("query", "")
                result = self.query_knowledge_base(query)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result["response"]
                            }
                        ],
                        "isError": False
                    }
                }

        # Default response for unhandled methods
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    def run(self):
        """Run the MCP server"""
        logger.info(f"Starting Timber MCP Protocol Server - Mode: {'LOCAL' if LOCAL_MODE else 'BEDROCK'}")
        
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    request = json.loads(line)
                    logger.info(f"Received request: {request.get('method', 'unknown')}")
                    response = self.handle_request(request)
                    print(json.dumps(response), flush=True)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if 'request' in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": "Internal error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    server = MCPServer()
    server.run()