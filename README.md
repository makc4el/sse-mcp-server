# SSE MCP Server

A Model Context Protocol (MCP) server with Server-Sent Events support following the official MCP specification for HTTP with SSE transport. Built in Python using FastAPI, this server provides testing tools for mathematical operations and is fully deployable on Railway platform.

## Features

- **MCP Protocol Compliance**: Implements MCP 2024-11-05 specification for HTTP with SSE transport
- **Proper SSE Flow**: Follows the official MCP SSE lifecycle with endpoint events
- **Session Management**: Supports multiple simultaneous SSE connections
- **Real-time Notifications**: Server-sent logging messages during tool execution
- **Testing Tools**: Built-in mathematical operation tools
- **Railway Ready**: Configured for easy deployment on Railway platform

## Available Tools

1. **add_numbers**: Calculate the sum of two numbers
2. **find_max**: Find the larger of two numbers

## API Endpoints

Following the [MCP specification](https://levelup.gitconnected.com/mcp-server-and-client-with-sse-the-new-streamable-http-d860850d9d9d):

- `GET /` - Server information and available endpoints
- `GET /health` - Health check endpoint
- `GET /connect` - **SSE connection endpoint** (establishes connection and sends endpoint event)
- `POST /messages` - **Message endpoint** (handles MCP JSON-RPC messages with sessionId)
- `GET /sse` - Legacy endpoint (provides guidance to proper MCP flow)

## MCP SSE Flow

The server implements the official MCP SSE lifecycle:

1. **Connection**: Client sends `GET /connect` to establish SSE connection
2. **Endpoint Event**: Server responds with endpoint event containing relative URI for messages
3. **Messaging**: Client sends JSON-RPC messages to the URI from the endpoint event
4. **Notifications**: Server can send real-time notifications via the SSE stream

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sse-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python main.py
```

The server will start on `http://localhost:8000` by default.

## Usage Examples

### MCP SSE Client Flow

```python
import httpx
import json
from urllib.parse import urlparse, parse_qs

# 1. Establish SSE connection
async with httpx.AsyncClient() as client:
    async with client.stream("GET", "http://localhost:8000/connect") as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("method") == "endpoint":
                    message_endpoint = f"http://localhost:8000{event['params']['uri']}"
                    break

# 2. Send MCP messages
message = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "add_numbers",
        "arguments": {"a": 15, "b": 25}
    }
}
response = await client.post(message_endpoint, json=message)
```

### JavaScript SSE Client

```javascript
// Establish SSE connection
const eventSource = new EventSource('http://localhost:8000/connect');
let messageEndpoint = null;

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.method === 'endpoint') {
    messageEndpoint = `http://localhost:8000${data.params.uri}`;
    console.log('Message endpoint:', messageEndpoint);
  } else if (data.method?.startsWith('notifications/')) {
    console.log('Notification:', data);
  }
};

// Send messages after getting endpoint
async function callTool() {
  const response = await fetch(messageEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: "1", 
      method: "tools/call",
      params: { name: "add_numbers", arguments: {a: 15, b: 25} }
    })
  });
  return response.json();
}
```

## Testing

### Manual Testing

Run the included test client to verify MCP SSE compliance:

```bash
python test_client.py
```

The test client will:
1. ✅ Verify server health
2. 🔗 Establish proper SSE connection via `/connect`
3. 📡 Receive endpoint event with message URI
4. 🔧 Initialize MCP connection
5. 📋 List available tools
6. ➕ Test `add_numbers` tool with real-time notifications
7. 🔢 Test `find_max` tool with real-time notifications

### Automated Testing

Install test dependencies:
```bash
pip install -r test_requirements.txt
```

Run all tests:
```bash
python run_tests.py
```

Run specific test types:
```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Tests with coverage report
python run_tests.py coverage
```

Or use pytest directly:
```bash
# All tests with coverage
pytest -v --cov=main test_unit.py test_integration.py

# Unit tests only
pytest -v test_unit.py

# Integration tests only
pytest -v test_integration.py
```

### Load Testing

Test server performance under load:

```bash
# Light load (5 concurrent clients)
python test_load.py light

# Medium load (20 concurrent clients)
python test_load.py medium

# Heavy load (50 concurrent clients)
python test_load.py heavy

# Stress test (increasing load)
python test_load.py stress
```

### Test Coverage

The test suite includes:

- **Unit Tests** (`test_unit.py`):
  - MCP message handlers
  - Tool functions
  - SSE helper functions
  - Tool definitions validation
  
- **Integration Tests** (`test_integration.py`):
  - HTTP endpoints
  - SSE connection flow
  - Complete MCP protocol flow
  - Session management
  - Error handling
  - Concurrent connections

- **Load Tests** (`test_load.py`):
  - Concurrent client simulation
  - Performance metrics
  - Stress testing
  - RPS (Requests Per Second) measurement

Expected output shows proper MCP SSE flow with session management and real-time notifications.

## Railway Deployment

This server is configured for deployment on Railway platform with the following files:

- `Procfile` - Defines the web process
- `runtime.txt` - Specifies Python version
- `railway.json` - Railway-specific configuration

### Deploy to Railway

1. **Via Railway CLI:**
```bash
npm install -g @railway/cli
railway login
railway init
railway deploy
```

2. **Via GitHub Integration:**
   - Connect your GitHub repository to Railway
   - Railway will automatically detect the configuration
   - Deploy with one click

3. **Environment Variables:**
   - `PORT` - Will be automatically set by Railway
   - `HOST` - Set to `0.0.0.0` (default)

### Railway Configuration

The server automatically detects Railway environment:
- Uses `PORT` environment variable provided by Railway
- Binds to `0.0.0.0` for external access
- Includes health check endpoint at `/health`
- Configured for automatic restarts on failure

## Project Structure

```
sse-mcp-server/
├── main.py              # Main server application
├── requirements.txt     # Python dependencies
├── test_requirements.txt # Testing dependencies
├── Procfile            # Railway process definition
├── runtime.txt         # Python runtime version
├── railway.json        # Railway deployment config
├── pytest.ini          # Pytest configuration
├── test_client.py      # Manual test client
├── test_unit.py        # Unit tests
├── test_integration.py # Integration tests
├── test_load.py        # Load/stress tests
├── run_tests.py        # Test runner script
├── .gitignore          # Git ignore patterns
└── README.md           # This file
```

## Development

### Adding New Tools

To add new tools, extend the `TOOLS` list in `main.py`:

```python
TOOLS.append(Tool(
    name="your_tool_name",
    description="Tool description",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    }
))
```

Then implement the tool function and add it to the `handle_call_tool` function.

### Environment Variables

- `PORT` - Server port (default: 8000)
- `HOST` - Server host (default: 0.0.0.0)

## Dependencies

- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server implementation
- **Pydantic**: Data validation using Python type annotations
- **MCP**: Model Context Protocol implementation
- **httpx**: HTTP client for testing

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the Railway deployment logs if deploying
- Ensure all dependencies are installed correctly
- Test locally before deploying
- Use the included test client to validate functionality

