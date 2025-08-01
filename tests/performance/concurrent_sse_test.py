#!/usr/bin/env python3
"""
Concurrent SSE streaming test for QaAI Assistant
Tests multiple simultaneous SSE connections
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any


async def single_sse_stream_test(session: aiohttp.ClientSession, base_url: str, user_id: int, query: str) -> Dict[str, Any]:
    """Test a single SSE stream"""
    start_time = time.time()
    
    payload = {
        "mode": "assist",
        "prompt": query,
        "jurisdiction": "DIFC", 
        "model": "gpt-4o-mini"
    }
    
    try:
        async with session.post(
            f"{base_url}/api/assistant/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status != 200:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "duration": time.time() - start_time
                }
            
            # Process SSE stream
            events_received = 0
            thinking_states = 0
            text_chunks = 0
            citations_received = 0
            last_event_time = start_time
            
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        events_received += 1
                        last_event_time = time.time()
                        
                        event_type = data.get('type')
                        if event_type == 'thinking_state':
                            thinking_states += 1
                        elif event_type == 'text_chunk':
                            text_chunks += 1
                        elif event_type == 'citations':
                            citations_received += len(data.get('citations', []))
                            
                    except json.JSONDecodeError:
                        continue
            
            total_duration = time.time() - start_time
            
            return {
                "user_id": user_id,
                "success": True,
                "duration": total_duration,
                "events_received": events_received,
                "thinking_states": thinking_states,
                "text_chunks": text_chunks,
                "citations_received": citations_received,
                "events_per_second": events_received / total_duration if total_duration > 0 else 0,
                "query_length": len(query)
            }
            
    except asyncio.TimeoutError:
        return {
            "user_id": user_id,
            "success": False,
            "error": "Timeout",
            "duration": time.time() - start_time
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }


async def concurrent_sse_test(base_url: str, concurrent_users: int = 5, timeout_seconds: int = 30):
    """Run concurrent SSE streaming test"""
    
    test_queries = [
        "What are the key employment law requirements in DIFC?",
        "Explain the data protection compliance framework for DIFC entities",
        "What are the regulatory reporting obligations for DFSA licensed firms?",
        "How should DIFC companies implement corporate governance policies?",
        "What are the anti-money laundering requirements in DIFC?",
        "Explain the dispute resolution mechanisms available in DIFC",
        "What are the capital adequacy requirements for financial institutions?",
        "How do DIFC employment contracts differ from UAE mainland contracts?"
    ]
    
    print(f"Testing {concurrent_users} concurrent SSE streams...")
    print(f"Timeout: {timeout_seconds} seconds")
    
    # Create sessions with proper timeouts
    connector = aiohttp.TCPConnector(limit=concurrent_users + 5)
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # Create concurrent tasks
        tasks = []
        for user_id in range(concurrent_users):
            query = test_queries[user_id % len(test_queries)]
            task = single_sse_stream_test(session, base_url, user_id, query)
            tasks.append(task)
        
        # Run all concurrent streams
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Process results (handle exceptions)
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "user_id": i,
                    "success": False,
                    "error": str(result),
                    "duration": total_duration
                })
            else:
                processed_results.append(result)
        
        return processed_results, total_duration


def analyze_concurrent_results(results: List[Dict[str, Any]], total_duration: float):
    """Analyze concurrent SSE test results"""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print("\n" + "="*60)
    print("CONCURRENT SSE STREAMING RESULTS")
    print("="*60)
    
    print(f"Concurrent Users: {len(results)}")
    print(f"Successful Streams: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"Failed Streams: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    print(f"Total Test Duration: {total_duration:.2f}s")
    
    if successful:
        durations = [r['duration'] for r in successful]
        events_received = [r['events_received'] for r in successful]
        thinking_states = [r['thinking_states'] for r in successful]
        text_chunks = [r['text_chunks'] for r in successful]
        
        print(f"\nStream Performance:")
        print(f"  Average Duration: {sum(durations)/len(durations):.2f}s")
        print(f"  Min Duration: {min(durations):.2f}s")
        print(f"  Max Duration: {max(durations):.2f}s")
        
        print(f"\nSSE Events:")
        print(f"  Total Events Received: {sum(events_received)}")
        print(f"  Average Events per Stream: {sum(events_received)/len(events_received):.1f}")
        print(f"  Total Thinking States: {sum(thinking_states)}")
        print(f"  Total Text Chunks: {sum(text_chunks)}")
        
        # Calculate throughput
        total_events = sum(events_received)
        if total_duration > 0:
            print(f"  Events per Second (system): {total_events/total_duration:.1f}")
        
        # Individual stream analysis
        print(f"\nIndividual Stream Analysis:")
        for result in successful:
            user_id = result['user_id']
            duration = result['duration']
            events = result['events_received']
            eps = result.get('events_per_second', 0)
            print(f"  User {user_id}: {events} events in {duration:.2f}s ({eps:.1f} eps)")
    
    if failed:
        print(f"\nFailure Analysis:")
        error_counts = {}
        for result in failed:
            error = result.get('error', 'Unknown')
            error_counts[error] = error_counts.get(error, 0) + 1
        
        for error, count in error_counts.items():
            print(f"  {error}: {count} occurrences")
    
    # Performance assessment
    print(f"\nPerformance Assessment:")
    success_rate = len(successful) / len(results)
    
    if success_rate >= 0.95:
        print("  ✅ Excellent concurrent performance (≥95% success)")
    elif success_rate >= 0.85:
        print("  ✅ Good concurrent performance (≥85% success)")
    elif success_rate >= 0.70:
        print("  ⚠️  Acceptable concurrent performance (≥70% success)")
    else:
        print("  ❌ Poor concurrent performance (<70% success)")
    
    if successful:
        avg_duration = sum(durations) / len(durations)
        if avg_duration <= 10:
            print("  ✅ Good response times (≤10s average)")
        elif avg_duration <= 20:
            print("  ⚠️  Acceptable response times (≤20s average)")
        else:
            print("  ❌ Slow response times (>20s average)")
    
    # Recommendations
    print(f"\nRecommendations:")
    if len(failed) > 0:
        print("  • Some streams failed - check server capacity and timeout settings")
    if successful and sum(durations)/len(durations) > 15:
        print("  • Streams are taking longer than expected - consider model optimization")
    if len(successful) == len(results) and sum(durations)/len(durations) < 10:
        print("  • Concurrent SSE performance is excellent!")


async def stress_test_sse(base_url: str):
    """Run progressive stress test"""
    print("\n" + "="*60)
    print("SSE STRESS TEST - Progressive Load")
    print("="*60)
    
    user_counts = [2, 5, 8, 10]
    
    for users in user_counts:
        print(f"\nTesting {users} concurrent users...")
        results, duration = await concurrent_sse_test(base_url, users, timeout_seconds=25)
        
        successful = len([r for r in results if r['success']])
        success_rate = successful / len(results)
        
        print(f"  Success Rate: {successful}/{users} ({success_rate*100:.1f}%)")
        print(f"  Test Duration: {duration:.2f}s")
        
        # If success rate drops below 80%, we've hit a limit
        if success_rate < 0.8:
            print(f"  ⚠️  Performance degradation detected at {users} users")
            break
        else:
            print(f"  ✅ System handled {users} concurrent users well")
        
        # Brief pause between tests
        await asyncio.sleep(2)


async def main():
    """Main concurrent SSE testing function"""
    base_url = "http://localhost:8000"
    
    print("QaAI Concurrent SSE Streaming Test")
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
                health_data = await response.json()
                print(f"Server Status: {health_data.get('status', 'unknown')}")
                print(f"Models Available: {health_data.get('models', {}).get('available', 0)}")
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return
    
    # Run standard concurrent test
    results, duration = await concurrent_sse_test(base_url, concurrent_users=5, timeout_seconds=30)
    analyze_concurrent_results(results, duration)
    
    # Run stress test
    await stress_test_sse(base_url)
    
    print("\nConcurrent SSE testing completed!")


if __name__ == "__main__":
    asyncio.run(main())