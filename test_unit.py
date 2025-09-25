#!/usr/bin/env python3
"""
Unit tests for SSE MCP Server
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from main import (
    handle_initialize,
    handle_list_tools,
    handle_call_tool,
    add_numbers,
    find_max,
    send_sse_event,
    sessions,
    TOOLS
)


class TestMCPHandlers:
    """Test MCP message handlers"""

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize handler"""
        result = await handle_initialize()
        
        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "sse-mcp-server"
        assert result["serverInfo"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test list tools handler"""
        result = await handle_list_tools()
        
        assert "tools" in result
        assert len(result["tools"]) == 2
        
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "add_numbers" in tool_names
        assert "find_max" in tool_names

    @pytest.mark.asyncio
    async def test_handle_call_tool_add_numbers(self):
        """Test call tool handler for add_numbers"""
        params = {
            "name": "add_numbers",
            "arguments": {"a": 15, "b": 25}
        }
        
        result = await handle_call_tool(params)
        
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        
        # Parse the JSON content
        content_data = json.loads(result["content"][0]["text"])
        assert content_data["operation"] == "addition"
        assert content_data["result"] == 40
        assert content_data["inputs"]["a"] == 15
        assert content_data["inputs"]["b"] == 25

    @pytest.mark.asyncio
    async def test_handle_call_tool_find_max(self):
        """Test call tool handler for find_max"""
        params = {
            "name": "find_max",
            "arguments": {"a": 42, "b": 37}
        }
        
        result = await handle_call_tool(params)
        
        assert "content" in result
        content_data = json.loads(result["content"][0]["text"])
        assert content_data["operation"] == "find_maximum"
        assert content_data["result"] == 42
        assert content_data["inputs"]["a"] == 42
        assert content_data["inputs"]["b"] == 37

    @pytest.mark.asyncio
    async def test_handle_call_tool_with_session_id(self):
        """Test call tool handler with session ID for notifications"""
        session_id = "test-session-123"
        sessions[session_id] = {"queue": AsyncMock()}
        
        params = {
            "name": "add_numbers",
            "arguments": {"a": 10, "b": 5}
        }
        
        result = await handle_call_tool(params, session_id)
        
        assert "content" in result
        content_data = json.loads(result["content"][0]["text"])
        assert content_data["result"] == 15
        
        # Clean up
        del sessions[session_id]

    @pytest.mark.asyncio
    async def test_handle_call_tool_missing_params(self):
        """Test call tool handler with missing parameters"""
        with pytest.raises(Exception):
            await handle_call_tool(None)

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self):
        """Test call tool handler with unknown tool"""
        params = {
            "name": "unknown_tool",
            "arguments": {}
        }
        
        with pytest.raises(Exception) as exc_info:
            await handle_call_tool(params)
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_call_tool_missing_arguments(self):
        """Test call tool handler with missing arguments"""
        params = {
            "name": "add_numbers",
            "arguments": {"a": 5}  # Missing 'b'
        }
        
        with pytest.raises(Exception) as exc_info:
            await handle_call_tool(params)
        assert "Missing required arguments" in str(exc_info.value.detail)


class TestToolFunctions:
    """Test individual tool functions"""

    @pytest.mark.asyncio
    async def test_add_numbers(self):
        """Test add_numbers function"""
        result = await add_numbers(10, 20)
        
        assert result["operation"] == "addition"
        assert result["result"] == 30
        assert result["inputs"]["a"] == 10
        assert result["inputs"]["b"] == 20

    @pytest.mark.asyncio
    async def test_add_numbers_negative(self):
        """Test add_numbers with negative numbers"""
        result = await add_numbers(-5, 3)
        
        assert result["result"] == -2

    @pytest.mark.asyncio
    async def test_add_numbers_floats(self):
        """Test add_numbers with floating point numbers"""
        result = await add_numbers(1.5, 2.5)
        
        assert result["result"] == 4.0

    @pytest.mark.asyncio
    async def test_find_max(self):
        """Test find_max function"""
        result = await find_max(42, 37)
        
        assert result["operation"] == "find_maximum"
        assert result["result"] == 42
        assert result["inputs"]["a"] == 42
        assert result["inputs"]["b"] == 37

    @pytest.mark.asyncio
    async def test_find_max_equal(self):
        """Test find_max with equal numbers"""
        result = await find_max(5, 5)
        
        assert result["result"] == 5

    @pytest.mark.asyncio
    async def test_find_max_negative(self):
        """Test find_max with negative numbers"""
        result = await find_max(-10, -5)
        
        assert result["result"] == -5

    @pytest.mark.asyncio
    async def test_find_max_floats(self):
        """Test find_max with floating point numbers"""
        result = await find_max(3.14, 2.71)
        
        assert result["result"] == 3.14


class TestSSEHelpers:
    """Test SSE helper functions"""

    @pytest.mark.asyncio
    async def test_send_sse_event_new_session(self):
        """Test sending SSE event to new session - should return early"""
        session_id = "test-session-new"
        initial_session_count = len(sessions)
        
        # Should return early since session doesn't exist
        await send_sse_event(session_id, "test_event", {"message": "hello"})
        
        # Session should not be created
        assert session_id not in sessions
        assert len(sessions) == initial_session_count

    @pytest.mark.asyncio
    async def test_send_sse_event_existing_session(self):
        """Test sending SSE event to existing session"""
        session_id = "test-session-existing"
        mock_queue = AsyncMock()
        sessions[session_id] = {"queue": mock_queue}
        
        test_data = {"message": "test"}
        await send_sse_event(session_id, "notification", test_data)
        
        mock_queue.put.assert_called_once_with({
            "type": "notification",
            "data": test_data
        })
        
        # Clean up
        del sessions[session_id]

    @pytest.mark.asyncio
    async def test_send_sse_event_nonexistent_session(self):
        """Test sending SSE event to nonexistent session"""
        # Should not raise an error
        await send_sse_event("nonexistent-session", "test", {})


class TestToolDefinitions:
    """Test tool definitions"""

    def test_tools_structure(self):
        """Test that TOOLS is properly structured"""
        assert len(TOOLS) == 2
        
        for tool in TOOLS:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema
            assert "required" in tool.inputSchema

    def test_add_numbers_tool_definition(self):
        """Test add_numbers tool definition"""
        add_tool = next(tool for tool in TOOLS if tool.name == "add_numbers")
        
        assert add_tool.description == "Calculate the sum of two numbers"
        assert "a" in add_tool.inputSchema["properties"]
        assert "b" in add_tool.inputSchema["properties"]
        assert add_tool.inputSchema["required"] == ["a", "b"]

    def test_find_max_tool_definition(self):
        """Test find_max tool definition"""
        max_tool = next(tool for tool in TOOLS if tool.name == "find_max")
        
        assert max_tool.description == "Find the larger of two numbers"
        assert "a" in max_tool.inputSchema["properties"]
        assert "b" in max_tool.inputSchema["properties"]
        assert max_tool.inputSchema["required"] == ["a", "b"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
