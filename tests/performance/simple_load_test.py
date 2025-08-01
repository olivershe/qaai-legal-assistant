#!/usr/bin/env python3
"""
Simple load testing script for QaAI system
Tests basic performance and concurrent access
"""

import asyncio
import aiohttp
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any


async def test_health_endpoint(session: aiohttp.ClientSession, base_url: str) -> Dict[str, Any]:
    """Test health endpoint performance"""
    start_time = time.time()
    try:
        async with session.get(f"{base_url}/health") as response:
            duration = time.time() - start_time
            result = await response.json()
            return {
                "endpoint": "health",
                "status_code": response.status,
                "duration": duration,
                "success": response.status == 200,
                "response_size": len(str(result))
            }
    except Exception as e:
        return {
            "endpoint": "health", 
            "status_code": 0,
            "duration": time.time() - start_time,
            "success": False,
            "error": str(e)
        }


async def test_assistant_query(session: aiohttp.ClientSession, base_url: str, query: str) -> Dict[str, Any]:
    """Test assistant query performance"""
    start_time = time.time()
    try:
        payload = {
            "mode": "assist",
            "prompt": query,
            "jurisdiction": "DIFC",
            "model": "gpt-4o-mini"
        }
        
        async with session.post(
            f"{base_url}/api/assistant/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                # Count SSE events
                events_count = 0
                thinking_states = 0
                text_chunks = 0
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            events_count += 1
                            if data.get('type') == 'thinking_state':
                                thinking_states += 1  
                            elif data.get('type') == 'text_chunk':
                                text_chunks += 1
                        except json.JSONDecodeError:
                            continue
                
                duration = time.time() - start_time
                return {
                    "endpoint": "assistant_query",
                    "status_code": response.status,
                    "duration": duration,
                    "success": True,
                    "events_count": events_count,
                    "thinking_states": thinking_states,
                    "text_chunks": text_chunks,
                    "query_length": len(query)
                }
            else:
                return {
                    "endpoint": "assistant_query",
                    "status_code": response.status,
                    "duration": time.time() - start_time,
                    "success": False,
                    "error": f"HTTP {response.status}"
                }
                
    except Exception as e:
        return {
            "endpoint": "assistant_query",
            "status_code": 0,
            "duration": time.time() - start_time,
            "success": False,
            "error": str(e)
        }


async def test_vault_projects(session: aiohttp.ClientSession, base_url: str) -> Dict[str, Any]:
    """Test vault projects endpoint"""
    start_time = time.time()
    try:
        async with session.get(f"{base_url}/api/vault/projects") as response:
            duration = time.time() - start_time
            if response.status == 200:
                result = await response.json()
                return {
                    "endpoint": "vault_projects",
                    "status_code": response.status,
                    "duration": duration,
                    "success": True,
                    "projects_count": len(result)
                }
            else:
                return {
                    "endpoint": "vault_projects",
                    "status_code": response.status,
                    "duration": duration,
                    "success": False,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            "endpoint": "vault_projects",
            "status_code": 0,
            "duration": time.time() - start_time,
            "success": False,
            "error": str(e)
        }


async def concurrent_load_test(base_url: str, concurrent_users: int = 5, requests_per_user: int = 3):
    """Run concurrent load test"""
    print(f"Running concurrent load test: {concurrent_users} users, {requests_per_user} requests each")
    
    test_queries = [
        "What are DIFC employment termination procedures?",
        "Explain data protection requirements in DIFC",
        "What are DFSA licensing requirements?",
        "How should companies handle regulatory compliance?",
        "What are corporate governance requirements?"
    ]
    
    async def user_session(user_id: int):
        """Simulate a user session"""
        results = []
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for request_num in range(requests_per_user):
                # Mix of different endpoint types
                if request_num % 3 == 0:
                    result = await test_health_endpoint(session, base_url)
                elif request_num % 3 == 1:
                    result = await test_vault_projects(session, base_url)
                else:
                    query = test_queries[request_num % len(test_queries)]
                    result = await test_assistant_query(session, base_url, query)
                
                result['user_id'] = user_id
                result['request_number'] = request_num
                results.append(result)
                
                # Brief pause between requests
                await asyncio.sleep(0.5)
        
        return results
    
    # Run concurrent user sessions
    start_time = time.time()
    tasks = [user_session(i) for i in range(concurrent_users)]
    all_results = await asyncio.gather(*tasks)
    total_duration = time.time() - start_time
    
    # Flatten results
    flat_results = []
    for user_results in all_results:
        flat_results.extend(user_results)
    
    return flat_results, total_duration


def analyze_results(results: List[Dict[str, Any]], total_duration: float):
    """Analyze load test results"""
    if not results:
        print("No results to analyze")
        return
    
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]
    
    print("\n" + "="*60)
    print("LOAD TEST RESULTS")
    print("="*60)
    
    print(f"Total Requests: {len(results)}")
    print(f"Successful: {len(successful_results)} ({len(successful_results)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failed_results)} ({len(failed_results)/len(results)*100:.1f}%)")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Requests/second: {len(results)/total_duration:.2f}")
    
    if successful_results:
        durations = [r['duration'] for r in successful_results]
        print(f"\nResponse Time Statistics:")
        print(f"  Average: {statistics.mean(durations):.3f}s")
        print(f"  Median: {statistics.median(durations):.3f}s")
        print(f"  Min: {min(durations):.3f}s")
        print(f"  Max: {max(durations):.3f}s")
        print(f"  95th percentile: {sorted(durations)[int(0.95 * len(durations))]:.3f}s")
    
    # Breakdown by endpoint
    endpoints = {}
    for result in successful_results:
        endpoint = result['endpoint']
        if endpoint not in endpoints:
            endpoints[endpoint] = []
        endpoints[endpoint].append(result['duration'])
    
    print(f"\nEndpoint Performance:")
    for endpoint, durations in endpoints.items():
        avg_duration = statistics.mean(durations)
        count = len(durations)
        print(f"  {endpoint}: {count} requests, avg {avg_duration:.3f}s")
    
    # Error analysis
    if failed_results:
        print(f"\nErrors:")
        error_types = {}
        for result in failed_results:
            error = result.get('error', f"HTTP {result['status_code']}")
            if error not in error_types:
                error_types[error] = 0
            error_types[error] += 1
        
        for error, count in error_types.items():
            print(f"  {error}: {count} occurrences")
    
    # Performance recommendations
    print(f"\nRecommendations:")
    avg_duration = statistics.mean([r['duration'] for r in successful_results]) if successful_results else 0
    
    if avg_duration > 10:
        print("  • Response times are high (>10s). Consider optimization.")
    if len(failed_results) > len(results) * 0.05:
        print("  • Error rate is high (>5%). Check system stability.")
    if len(results)/total_duration < 1:
        print("  • Low throughput (<1 req/s). Consider scaling.")
    
    if avg_duration < 5 and len(failed_results) == 0:
        print("  • Performance looks good!")


async def run_security_tests(base_url: str):
    """Run basic security tests"""
    print("\n" + "="*60)
    print("SECURITY VALIDATION")
    print("="*60)
    
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Test CORS headers
        try:
            async with session.options(f"{base_url}/api/assistant/query") as response:
                cors_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
                }
                print("CORS Configuration:")
                for header, value in cors_headers.items():
                    print(f"  {header}: {value or 'Not set'}")
        except Exception as e:
            print(f"CORS test failed: {e}")
        
        # Test rate limiting (attempt rapid requests)
        print(f"\nRate Limiting Test:")
        rapid_requests = []
        for i in range(20):  # Try 20 rapid requests
            start = time.time()
            try:
                async with session.get(f"{base_url}/health") as response:
                    duration = time.time() - start
                    rapid_requests.append({
                        'request': i,
                        'status': response.status,
                        'duration': duration
                    })
            except Exception as e:
                rapid_requests.append({
                    'request': i,
                    'status': 0,
                    'error': str(e)
                })
        
        # Analyze rate limiting
        successful_rapid = [r for r in rapid_requests if r.get('status') == 200]
        failed_rapid = [r for r in rapid_requests if r.get('status') != 200]
        
        print(f"  Rapid requests successful: {len(successful_rapid)}/20")
        print(f"  Rapid requests failed: {len(failed_rapid)}/20")
        
        if len(failed_rapid) > 0:
            print("  • Rate limiting appears to be active")
        else:
            print("  • No rate limiting detected (may need configuration)")


async def main():
    """Main performance testing function"""
    base_url = "http://localhost:8000"
    
    print("Starting QaAI Performance Testing Suite")
    print("="*60)
    
    # Test server availability
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=10)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(f"{base_url}/health") as response:
                if response.status != 200:
                    print(f"Server not healthy: {response.status}")
                    return
                print("Server is running and healthy")
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return
    
    # Run concurrent load test
    results, duration = await concurrent_load_test(base_url, 
                                                  concurrent_users=3, 
                                                  requests_per_user=4)
    
    analyze_results(results, duration)
    
    # Run security tests
    await run_security_tests(base_url)
    
    print("\nPerformance testing completed!")


if __name__ == "__main__":
    asyncio.run(main())