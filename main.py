#!/usr/bin/env python3
"""
SSE MCP Server - A basic Model Context Protocol server with Server-Sent Events support
Following MCP specification for HTTP with SSE transport
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SSE MCP Server",
    description="A basic MCP server with Server-Sent Events support following MCP specification",
    version="1.0.0"
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session management for multiple connections
sessions: Dict[str, Dict[str, Any]] = {}

# Pydantic models for MCP protocol
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class ToolInput(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

# Tool definitions
TOOLS = [
    Tool(
        name="add_numbers",
        description="Calculate the sum of two numbers",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    ),
    Tool(
        name="find_max",
        description="Find the larger of two numbers",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )
]

# Tool implementations
async def add_numbers(a: float, b: float) -> Dict[str, Any]:
    """Add two numbers and return the sum"""
    result = a + b
    logger.info(f"Adding {a} + {b} = {result}")
    return {
        "operation": "addition",
        "inputs": {"a": a, "b": b},
        "result": result
    }

async def find_max(a: float, b: float) -> Dict[str, Any]:
    """Find the maximum of two numbers"""
    result = max(a, b)
    logger.info(f"Finding max of {a} and {b} = {result}")
    return {
        "operation": "find_maximum",
        "inputs": {"a": a, "b": b},
        "result": result
    }

# Helper functions for SSE
async def send_sse_event(session_id: str, event_type: str, data: Any):
    """Send SSE event to a specific session"""
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    if "queue" not in session:
        session["queue"] = asyncio.Queue()
    
    await session["queue"].put({
        "type": event_type,
        "data": data
    })

# MCP message handlers
async def handle_initialize(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle MCP initialize request"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            "logging": {}
        },
        "serverInfo": {
            "name": "sse-mcp-server",
            "version": "1.0.0"
        }
    }

async def handle_list_tools(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle tools/list request"""
    return {
        "tools": [tool.model_dump() for tool in TOOLS]
    }

async def handle_call_tool(params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle tools/call request"""
    if not params:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    # Send logging notifications if session_id is provided
    if session_id:
        await send_sse_event(session_id, "notification", {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {
                "level": "info", 
                "data": f"Calling tool: {tool_name}"
            }
        })
    
    if tool_name == "add_numbers":
        a = arguments.get("a")
        b = arguments.get("b")
        if a is None or b is None:
            raise HTTPException(status_code=400, detail="Missing required arguments 'a' and 'b'")
        result = await add_numbers(float(a), float(b))
        
        # Send logging notification
        if session_id:
            await send_sse_event(session_id, "notification", {
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "level": "info", 
                    "data": f"Addition result: {result['result']}"
                }
            })
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    elif tool_name == "find_max":
        a = arguments.get("a")
        b = arguments.get("b")
        if a is None or b is None:
            raise HTTPException(status_code=400, detail="Missing required arguments 'a' and 'b'")
        result = await find_max(float(a), float(b))
        
        # Send logging notification
        if session_id:
            await send_sse_event(session_id, "notification", {
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "level": "info", 
                    "data": f"Maximum result: {result['result']}"
                }
            })
        
        return {
            "content": [
                {
                    "type": "text", 
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

# Route handlers
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "SSE MCP Server",
        "version": "1.0.0",
        "description": "A basic MCP server with Server-Sent Events support following MCP specification",
        "endpoints": {
            "connect": "/connect",
            "messages": "/messages",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "sse-mcp-server"}

@app.get("/connect")
async def connect_sse(request: Request):
    """SSE connection endpoint - establishes connection and sends endpoint event"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "queue": asyncio.Queue(),
        "connected": True
    }
    
    logger.info(f"New SSE connection established with session ID: {session_id}")
    
    async def event_generator():
        try:
            # Send endpoint event as per MCP specification
            endpoint_event = {
                "jsonrpc": "2.0",
                "method": "endpoint",
                "params": {
                    "uri": f"/messages?sessionId={session_id}"
                }
            }
            yield f"data: {json.dumps(endpoint_event)}\n\n"
            
            # Send initial connection notification
            connection_event = {
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "level": "info",
                    "data": "SSE connection established"
                }
            }
            yield f"data: {json.dumps(connection_event)}\n\n"
            
            # Process queued events
            session = sessions[session_id]
            while session.get("connected", True):
                try:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break
                    
                    # Get event from queue with timeout
                    event = await asyncio.wait_for(session["queue"].get(), timeout=30.0)
                    yield f"data: {json.dumps(event['data'])}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = {
                        "jsonrpc": "2.0",
                        "method": "ping"
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
        finally:
            # Cleanup session
            if session_id in sessions:
                sessions[session_id]["connected"] = False
                del sessions[session_id]
            logger.info(f"SSE connection closed for session: {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.post("/messages")
async def handle_messages(request: MCPRequest, http_request: Request):
    """Handle MCP messages sent from client"""
    try:
        # Get session ID from query parameters
        session_id = http_request.query_params.get("sessionId")
        if not session_id or session_id not in sessions:
            raise HTTPException(status_code=400, detail="Invalid or missing sessionId")
        
        logger.info(f"Received MCP message for session {session_id}: {request.method}")
        
        if request.method == "initialize":
            result = await handle_initialize(request.params)
        elif request.method == "tools/list":
            result = await handle_list_tools(request.params)
        elif request.method == "tools/call":
            result = await handle_call_tool(request.params, session_id)
        else:
            raise HTTPException(status_code=404, detail=f"Method '{request.method}' not supported")
        
        response = MCPResponse(
            id=request.id,
            result=result
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling MCP message: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        )

# Legacy SSE endpoint for backwards compatibility
@app.get("/sse")
async def sse_endpoint(request: Request):
    """Legacy SSE endpoint - redirects to proper MCP SSE flow"""
    return {
        "message": "Please use /connect endpoint for proper MCP SSE connection",
        "endpoints": {
            "connect": "/connect",
            "messages": "/messages"
        },
        "flow": "1. GET /connect to establish SSE connection, 2. POST to URI from endpoint event"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting SSE MCP Server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

