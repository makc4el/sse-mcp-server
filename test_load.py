#!/usr/bin/env python3
"""
Load tests for SSE MCP Server
"""

import asyncio
import httpx
import time
import json
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import statistics


class LoadTester:
    """Load tester for MCP SSE server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def single_mcp_request(self, client_id: int) -> dict:
        """Perform a single MCP request flow"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Connect and get endpoint
                connect_start = time.time()
                message_endpoint = None
                
                async with client.stream("GET", f"{self.base_url}/connect") as response:
                    if response.status_code != 200:
                        raise Exception(f"Connect failed: {response.status_code}")
                        
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                event = json.loads(data)
                                if event.get("method") == "endpoint":
                                    message_endpoint = f"{self.base_url}{event['params']['uri']}"
                                    break
                            except json.JSONDecodeError:
                                pass
                
                connect_time = time.time() - connect_start
                
                if not message_endpoint:
                    raise Exception("Failed to get message endpoint")
                
                # Step 2: Initialize
                init_start = time.time()
                init_message = {
                    "jsonrpc": "2.0",
                    "id": f"init_{client_id}",
                    "method": "initialize",
                    "params": {}
                }
                
                response = await client.post(message_endpoint, json=init_message)
                if response.status_code != 200:
                    raise Exception(f"Initialize failed: {response.status_code}")
                    
                init_time = time.time() - init_start
                
                # Step 3: Call tool
                tool_start = time.time()
                tool_message = {
                    "jsonrpc": "2.0",
                    "id": f"tool_{client_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "add_numbers",
                        "arguments": {"a": client_id, "b": client_id * 2}
                    }
                }
                
                response = await client.post(message_endpoint, json=tool_message)
                if response.status_code != 200:
                    raise Exception(f"Tool call failed: {response.status_code}")
                    
                tool_time = time.time() - tool_start
                total_time = time.time() - start_time
                
                return {
                    "client_id": client_id,
                    "success": True,
                    "total_time": total_time,
                    "connect_time": connect_time,
                    "init_time": init_time,
                    "tool_time": tool_time,
                    "error": None
                }
                
        except Exception as e:
            total_time = time.time() - start_time
            return {
                "client_id": client_id,
                "success": False,
                "total_time": total_time,
                "connect_time": 0,
                "init_time": 0,
                "tool_time": 0,
                "error": str(e)
            }
    
    async def run_concurrent_test(self, num_clients: int = 10):
        """Run concurrent load test"""
        print(f"🚀 Starting load test with {num_clients} concurrent clients")
        print("-" * 50)
        
        start_time = time.time()
        
        # Create concurrent tasks
        tasks = [
            self.single_mcp_request(i) 
            for i in range(num_clients)
        ]
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        successful = [r for r in results if isinstance(r, dict) and r["success"]]
        failed = [r for r in results if isinstance(r, dict) and not r["success"]]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        print(f"📊 Load Test Results:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Successful requests: {len(successful)}/{num_clients}")
        print(f"   Failed requests: {len(failed)}")
        print(f"   Exceptions: {len(exceptions)}")
        
        if successful:
            times = [r["total_time"] for r in successful]
            connect_times = [r["connect_time"] for r in successful]
            init_times = [r["init_time"] for r in successful]
            tool_times = [r["tool_time"] for r in successful]
            
            print(f"\n⏱️  Timing Statistics:")
            print(f"   Average total time: {statistics.mean(times):.3f}s")
            print(f"   Median total time: {statistics.median(times):.3f}s")
            print(f"   Min/Max total time: {min(times):.3f}s / {max(times):.3f}s")
            print(f"   Average connect time: {statistics.mean(connect_times):.3f}s")
            print(f"   Average init time: {statistics.mean(init_times):.3f}s")
            print(f"   Average tool time: {statistics.mean(tool_times):.3f}s")
            
            # Requests per second
            rps = len(successful) / total_time
            print(f"   Requests per second: {rps:.2f}")
        
        if failed:
            print(f"\n❌ Failed Requests:")
            for failure in failed[:5]:  # Show first 5 failures
                print(f"   Client {failure['client_id']}: {failure['error']}")
        
        if exceptions:
            print(f"\n💥 Exceptions:")
            for exc in exceptions[:5]:  # Show first 5 exceptions
                print(f"   {exc}")
        
        return {
            "total_requests": num_clients,
            "successful": len(successful),
            "failed": len(failed),
            "exceptions": len(exceptions),
            "total_time": total_time,
            "rps": len(successful) / total_time if total_time > 0 else 0,
            "avg_response_time": statistics.mean([r["total_time"] for r in successful]) if successful else 0
        }
    
    async def run_stress_test(self, max_clients: int = 50, step: int = 10):
        """Run stress test with increasing load"""
        print(f"🔥 Starting stress test: 1 to {max_clients} clients (step: {step})")
        print("=" * 60)
        
        stress_results = []
        
        for num_clients in range(step, max_clients + 1, step):
            print(f"\n📈 Testing with {num_clients} clients...")
            result = await self.run_concurrent_test(num_clients)
            stress_results.append({
                "clients": num_clients,
                **result
            })
            
            # Brief pause between tests
            await asyncio.sleep(2)
        
        print(f"\n🏁 Stress Test Summary:")
        print("-" * 40)
        for result in stress_results:
            success_rate = (result["successful"] / result["total_requests"]) * 100
            print(f"   {result['clients']:2d} clients: "
                  f"{success_rate:5.1f}% success, "
                  f"{result['rps']:5.1f} RPS, "
                  f"{result['avg_response_time']:.3f}s avg")
        
        return stress_results


async def test_health_endpoint():
    """Test if server is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            return response.status_code == 200
    except:
        return False


async def main():
    """Main test function"""
    print("🧪 SSE MCP Server Load Testing")
    print("=" * 40)
    
    # Check if server is running
    if not await test_health_endpoint():
        print("❌ Server is not running!")
        print("   Start the server with: python main.py")
        return
    
    print("✅ Server is running")
    
    tester = LoadTester()
    
    # Run tests based on command line arguments
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "light":
            await tester.run_concurrent_test(5)
        elif sys.argv[1] == "medium":
            await tester.run_concurrent_test(20)
        elif sys.argv[1] == "heavy":
            await tester.run_concurrent_test(50)
        elif sys.argv[1] == "stress":
            await tester.run_stress_test(50, 10)
        else:
            print("Available options: light, medium, heavy, stress")
    else:
        # Default: medium load test
        await tester.run_concurrent_test(10)


if __name__ == "__main__":
    asyncio.run(main())

