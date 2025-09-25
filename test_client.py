#!/usr/bin/env python3
"""
Test client for the SSE MCP Server following MCP specification
"""

import asyncio
import json
import httpx
import time
from urllib.parse import urlparse, parse_qs

SERVER_URL = "http://localhost:8000"

class MCPSSEClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session_id = None
        self.message_endpoint = None
        self.notifications = []
        
    async def connect(self):
        """Establish SSE connection and get message endpoint"""
        print("Connecting to MCP SSE server...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", f"{self.server_url}/connect") as response:
                print(f"SSE Connection Status: {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(data)
                            print(f"Received event: {event}")
                            
                            # Handle endpoint event
                            if event.get("method") == "endpoint":
                                endpoint_uri = event["params"]["uri"]
                                self.message_endpoint = f"{self.server_url}{endpoint_uri}"
                                # Extract session ID from URI
                                parsed = urlparse(endpoint_uri)
                                query_params = parse_qs(parsed.query)
                                self.session_id = query_params.get("sessionId", [None])[0]
                                print(f"Message endpoint: {self.message_endpoint}")
                                print(f"Session ID: {self.session_id}")
                                break
                                
                            # Handle notifications
                            elif event.get("method", "").startswith("notifications/"):
                                self.notifications.append(event)
                                
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON: {data}, error: {e}")
                            
    async def send_message(self, message: dict) -> dict:
        """Send a message to the server"""
        if not self.message_endpoint:
            raise Exception("Not connected - call connect() first")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(self.message_endpoint, json=message)
            return response.json()
            
    async def initialize(self):
        """Initialize the MCP connection"""
        message = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {}
        }
        response = await self.send_message(message)
        print(f"Initialize response: {response}")
        return response
        
    async def list_tools(self):
        """List available tools"""
        message = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list"
        }
        response = await self.send_message(message)
        print(f"List tools response: {response}")
        return response
        
    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool"""
        message = {
            "jsonrpc": "2.0",
            "id": f"tool_{tool_name}_{int(time.time())}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        response = await self.send_message(message)
        print(f"Tool call response for {tool_name}: {response}")
        return response

async def test_mcp_sse_flow():
    """Test the complete MCP SSE flow"""
    print("Testing MCP SSE Flow...")
    
    client = MCPSSEClient(SERVER_URL)
    
    try:
        # 1. Connect and get endpoint
        await client.connect()
        
        if not client.message_endpoint:
            print("❌ Failed to establish SSE connection")
            return
            
        print("✅ SSE connection established")
        
        # 2. Initialize
        print("\n2. Initializing...")
        await client.initialize()
        
        # 3. List tools
        print("\n3. Listing tools...")
        await client.list_tools()
        
        # 4. Test add_numbers tool
        print("\n4. Testing add_numbers tool...")
        await client.call_tool("add_numbers", {"a": 15, "b": 25})
        
        # 5. Test find_max tool
        print("\n5. Testing find_max tool...")
        await client.call_tool("find_max", {"a": 42, "b": 37})
        
        # 6. Show any received notifications
        print(f"\n6. Received {len(client.notifications)} notifications:")
        for notification in client.notifications:
            print(f"   - {notification}")
            
    except Exception as e:
        print(f"❌ Error in MCP SSE flow: {e}")

async def test_legacy_endpoints():
    """Test legacy endpoints for compatibility"""
    print("\nTesting Legacy Endpoints...")
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        print("\n1. Testing root endpoint...")
        response = await client.get(f"{SERVER_URL}/")
        print(f"Root response: {response.json()}")
        
        # Test health endpoint
        print("\n2. Testing health endpoint...")
        response = await client.get(f"{SERVER_URL}/health")
        print(f"Health response: {response.json()}")
        
        # Test legacy SSE endpoint
        print("\n3. Testing legacy SSE endpoint...")
        response = await client.get(f"{SERVER_URL}/sse")
        print(f"Legacy SSE response: {response.json()}")

async def main():
    """Main test function"""
    print("SSE MCP Server Test Client")
    print("=" * 50)
    print("Following MCP specification for HTTP with SSE transport")
    print("=" * 50)
    
    # Test health endpoint first
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SERVER_URL}/health")
            print(f"Health check: {response.json()}")
        except Exception as e:
            print(f"❌ Server not running or health check failed: {e}")
            print("Make sure to start the server with: python main.py")
            return
    
    print("✅ Server is running")
    
    # Test legacy endpoints for compatibility
    await test_legacy_endpoints()
    
    # Test proper MCP SSE flow
    await test_mcp_sse_flow()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())

