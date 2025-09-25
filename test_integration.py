#!/usr/bin/env python3
"""
Integration tests for SSE MCP Server
"""

import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx
from main import app, sessions
from urllib.parse import urlparse, parse_qs


class TestBasicEndpoints:
    """Test basic HTTP endpoints"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "SSE MCP Server"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/connect" in data["endpoints"]["connect"]
        assert "/messages" in data["endpoints"]["messages"]

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["server"] == "sse-mcp-server"

    def test_legacy_sse_endpoint(self):
        """Test legacy SSE endpoint"""
        response = self.client.get("/sse")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "flow" in data


class TestSSEConnection:
    """Test SSE connection functionality"""

    @pytest.mark.asyncio
    async def test_sse_connect_endpoint(self):
        """Test SSE connection endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            async with client.stream("GET", "/connect") as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
                
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(data)
                            events.append(event)
                            
                            # Stop after getting endpoint event
                            if event.get("method") == "endpoint":
                                break
                                
                        except json.JSONDecodeError:
                            pass
                
                # Verify we got the endpoint event
                endpoint_event = next((e for e in events if e.get("method") == "endpoint"), None)
                assert endpoint_event is not None
                assert "params" in endpoint_event
                assert "uri" in endpoint_event["params"]
                assert endpoint_event["params"]["uri"].startswith("/messages?sessionId=")

    @pytest.mark.asyncio
    async def test_sse_session_management(self):
        """Test SSE session creation and cleanup"""
        initial_session_count = len(sessions)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            async with client.stream("GET", "/connect") as response:
                # Session should be created
                assert len(sessions) == initial_session_count + 1
                
                # Get the first event to extract session ID
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                uri = event["params"]["uri"]
                                parsed = urlparse(uri)
                                query_params = parse_qs(parsed.query)
                                session_id = query_params.get("sessionId", [None])[0]
                                assert session_id in sessions
                                break
                        except json.JSONDecodeError:
                            pass
        
        # Session should be cleaned up after connection closes
        # Note: In real scenarios, cleanup happens when connection closes
        # For testing, we verify the session was created


class TestMessageEndpoint:
    """Test message endpoint functionality"""

    @pytest.mark.asyncio
    async def test_messages_endpoint_without_session(self):
        """Test messages endpoint without valid session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            message = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {}
            }
            
            response = await client.post("/messages", json=message)
            assert response.status_code == 400
            assert "Invalid or missing sessionId" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_messages_endpoint_with_invalid_session(self):
        """Test messages endpoint with invalid session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            message = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {}
            }
            
            response = await client.post("/messages?sessionId=invalid", json=message)
            assert response.status_code == 400
            assert "Invalid or missing sessionId" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_full_mcp_flow(self):
        """Test complete MCP flow: connect -> get endpoint -> send messages"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Connect and get endpoint
            message_endpoint = None
            async with client.stream("GET", "/connect") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                message_endpoint = event["params"]["uri"]
                                break
                        except json.JSONDecodeError:
                            pass
            
            assert message_endpoint is not None
            
            # Step 2: Send initialize message
            init_message = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {}
            }
            
            response = await client.post(message_endpoint, json=init_message)
            assert response.status_code == 200
            
            result = response.json()
            assert result["jsonrpc"] == "2.0"
            assert result["id"] == "1"
            assert "result" in result
            assert result["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_tools_list_via_messages(self):
        """Test tools/list via messages endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get endpoint
            message_endpoint = None
            async with client.stream("GET", "/connect") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                message_endpoint = event["params"]["uri"]
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Send tools/list message
            list_message = {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/list"
            }
            
            response = await client.post(message_endpoint, json=list_message)
            assert response.status_code == 200
            
            result = response.json()
            assert "result" in result
            assert "tools" in result["result"]
            assert len(result["result"]["tools"]) == 2

    @pytest.mark.asyncio
    async def test_tool_call_via_messages(self):
        """Test tools/call via messages endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get endpoint
            message_endpoint = None
            async with client.stream("GET", "/connect") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                message_endpoint = event["params"]["uri"]
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Send tool call message
            call_message = {
                "jsonrpc": "2.0",
                "id": "3",
                "method": "tools/call",
                "params": {
                    "name": "add_numbers",
                    "arguments": {"a": 10, "b": 15}
                }
            }
            
            response = await client.post(message_endpoint, json=call_message)
            assert response.status_code == 200
            
            result = response.json()
            assert "result" in result
            assert "content" in result["result"]
            
            content_text = result["result"]["content"][0]["text"]
            content_data = json.loads(content_text)
            assert content_data["result"] == 25


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        """Test invalid method handling"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get endpoint
            message_endpoint = None
            async with client.stream("GET", "/connect") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                message_endpoint = event["params"]["uri"]
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Send invalid method
            invalid_message = {
                "jsonrpc": "2.0",
                "id": "4",
                "method": "invalid/method"
            }
            
            response = await client.post(message_endpoint, json=invalid_message)
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_malformed_tool_call(self):
        """Test malformed tool call handling"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get endpoint
            message_endpoint = None
            async with client.stream("GET", "/connect") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("method") == "endpoint":
                                message_endpoint = event["params"]["uri"]
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Send malformed tool call
            malformed_message = {
                "jsonrpc": "2.0",
                "id": "5",
                "method": "tools/call",
                "params": {
                    "name": "add_numbers",
                    "arguments": {"a": 10}  # Missing 'b'
                }
            }
            
            response = await client.post(message_endpoint, json=malformed_message)
            assert response.status_code == 400


class TestConcurrentConnections:
    """Test concurrent SSE connections"""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self):
        """Test multiple concurrent SSE connections"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Start multiple connections
            connection_tasks = []
            endpoints = []
            
            async def get_endpoint():
                async with client.stream("GET", "/connect") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                event = json.loads(data)
                                if event.get("method") == "endpoint":
                                    return event["params"]["uri"]
                            except json.JSONDecodeError:
                                pass
                return None
            
            # Create 3 concurrent connections
            tasks = [get_endpoint() for _ in range(3)]
            endpoints = await asyncio.gather(*tasks)
            
            # All should have unique endpoints
            assert len(endpoints) == 3
            assert len(set(endpoints)) == 3  # All unique
            
            # All should be valid endpoints
            for endpoint in endpoints:
                assert endpoint.startswith("/messages?sessionId=")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

