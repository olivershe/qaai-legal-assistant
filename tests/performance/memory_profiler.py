"""
Memory and CPU usage profiler for QaAI system
Monitors resource usage during various operations
"""

import asyncio
import time
import psutil
import aiohttp
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ResourceMetrics:
    """Resource usage metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int
    open_files: int
    threads: int


class SystemProfiler:
    """Profiles system resource usage during QaAI operations"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics: List[ResourceMetrics] = []
        self.process = psutil.Process()
        self.monitoring = False
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics"""
        # CPU usage
        cpu_percent = self.process.cpu_percent()
        
        # Memory usage
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = self.process.memory_percent()
        
        # Disk I/O (may not be available on macOS)
        try:
            disk_io = self.process.io_counters()
            disk_read = disk_io.read_bytes
            disk_write = disk_io.write_bytes
        except (AttributeError, psutil.AccessDenied):
            disk_read = 0
            disk_write = 0
        
        # Network I/O (system-wide since process-level not available)
        try:
            network_io = psutil.net_io_counters()
            net_sent = network_io.bytes_sent
            net_recv = network_io.bytes_recv
        except (AttributeError, psutil.AccessDenied):
            net_sent = 0
            net_recv = 0
        
        # Process info
        try:
            open_files = len(self.process.open_files())
        except (AttributeError, psutil.AccessDenied):
            open_files = 0
        
        threads = self.process.num_threads()
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_io_read=disk_read,
            disk_io_write=disk_write,
            network_bytes_sent=net_sent,
            network_bytes_recv=net_recv,
            open_files=open_files,
            threads=threads
        )
    
    async def monitor_resources(self, interval: float = 0.5):
        """Monitor resources continuously"""
        while self.monitoring:
            metrics = self.get_current_metrics()
            self.metrics.append(metrics)
            await asyncio.sleep(interval)
    
    async def profile_assistant_query(self, query: str, model: str = "gpt-4o-mini") -> Dict:
        """Profile resource usage during assistant query"""
        print(f"Profiling assistant query: {query[:50]}...")
        
        # Start monitoring
        self.monitoring = True
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        # Record baseline
        baseline = self.get_current_metrics()
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "mode": "assist",
                    "prompt": query,
                    "jurisdiction": "DIFC",
                    "model": model
                }
                
                async with session.post(
                    f"{self.base_url}/api/assistant/query",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        # Process SSE stream
                        chunks_processed = 0
                        thinking_states = 0
                        
                        async for line in response.content:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if data.get('type') == 'thinking_state':
                                        thinking_states += 1
                                    elif data.get('type') == 'text_chunk':
                                        chunks_processed += 1
                                except json.JSONDecodeError:
                                    continue
                        
                        duration = time.time() - start_time
                        
                        # Stop monitoring
                        self.monitoring = False
                        await monitor_task
                        
                        # Calculate peak usage
                        peak_metrics = self.calculate_peak_usage(baseline)
                        
                        return {
                            "operation": "assistant_query",
                            "query_length": len(query),
                            "duration": duration,
                            "chunks_processed": chunks_processed,
                            "thinking_states": thinking_states,
                            "baseline": asdict(baseline),
                            "peak_usage": peak_metrics,
                            "metrics_count": len(self.metrics)
                        }
                    else:
                        self.monitoring = False
                        await monitor_task
                        return {"error": f"HTTP {response.status}"}
                        
        except Exception as e:
            self.monitoring = False
            if not monitor_task.done():
                await monitor_task
            return {"error": str(e)}
    
    async def profile_rag_retrieval(self, query: str, top_k: int = 5) -> Dict:
        """Profile RAG retrieval performance"""
        print(f"Profiling RAG retrieval: {query[:50]}...")
        
        self.monitoring = True
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        baseline = self.get_current_metrics()
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "jurisdiction": "DIFC",
                    "top_k": top_k
                }
                
                async with session.post(
                    f"{self.base_url}/api/rag/search",
                    json=payload
                ) as response:
                    duration = time.time() - start_time
                    
                    self.monitoring = False
                    await monitor_task
                    
                    if response.status == 200:
                        result = await response.json()
                        peak_metrics = self.calculate_peak_usage(baseline)
                        
                        return {
                            "operation": "rag_retrieval",
                            "query_length": len(query),
                            "top_k": top_k,
                            "duration": duration,
                            "documents_found": len(result.get('documents', [])),
                            "baseline": asdict(baseline),
                            "peak_usage": peak_metrics,
                            "metrics_count": len(self.metrics)
                        }
                    else:
                        return {"error": f"HTTP {response.status}"}
                        
        except Exception as e:
            self.monitoring = False
            if not monitor_task.done():
                await monitor_task
            return {"error": str(e)}
    
    def calculate_peak_usage(self, baseline: ResourceMetrics) -> Dict:
        """Calculate peak resource usage compared to baseline"""
        if not self.metrics:
            return {}
        
        max_cpu = max(m.cpu_percent for m in self.metrics)
        max_memory = max(m.memory_mb for m in self.metrics)
        max_memory_pct = max(m.memory_percent for m in self.metrics)
        max_threads = max(m.threads for m in self.metrics)
        max_files = max(m.open_files for m in self.metrics)
        
        return {
            "peak_cpu_percent": max_cpu,
            "peak_memory_mb": max_memory,
            "peak_memory_percent": max_memory_pct,
            "peak_threads": max_threads,
            "peak_open_files": max_files,
            "cpu_increase": max_cpu - baseline.cpu_percent,
            "memory_increase_mb": max_memory - baseline.memory_mb,
            "thread_increase": max_threads - baseline.threads,
            "files_increase": max_files - baseline.open_files
        }
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Generate performance analysis report"""
        if not results:
            return {"error": "No results to analyze"}
        
        successful_results = [r for r in results if "error" not in r]
        
        if not successful_results:
            return {"error": "No successful operations to analyze"}
        
        # Calculate averages
        avg_duration = sum(r['duration'] for r in successful_results) / len(successful_results)
        avg_memory = sum(r['peak_usage']['peak_memory_mb'] for r in successful_results) / len(successful_results)
        avg_cpu = sum(r['peak_usage']['peak_cpu_percent'] for r in successful_results) / len(successful_results)
        
        # Find bottlenecks
        slow_operations = [r for r in successful_results if r['duration'] > avg_duration * 1.5]
        memory_intensive = [r for r in successful_results if r['peak_usage']['peak_memory_mb'] > avg_memory * 1.5]
        cpu_intensive = [r for r in successful_results if r['peak_usage']['peak_cpu_percent'] > avg_cpu * 1.5]
        
        return {
            "total_operations": len(results),
            "successful_operations": len(successful_results),
            "failed_operations": len(results) - len(successful_results),
            "average_duration": avg_duration,
            "average_memory_mb": avg_memory,
            "average_cpu_percent": avg_cpu,
            "performance_issues": {
                "slow_operations": len(slow_operations),
                "memory_intensive_operations": len(memory_intensive),
                "cpu_intensive_operations": len(cpu_intensive)
            },
            "recommendations": self.generate_recommendations(successful_results)
        }
    
    def generate_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Check average duration
        avg_duration = sum(r['duration'] for r in results) / len(results)
        if avg_duration > 10:
            recommendations.append("Average response time is high (>10s). Consider caching or model optimization.")
        
        # Check memory usage
        avg_memory = sum(r['peak_usage']['peak_memory_mb'] for r in results) / len(results)
        if avg_memory > 500:
            recommendations.append("High memory usage detected (>500MB). Consider memory optimization.")
        
        # Check for memory growth
        memory_increases = [r['peak_usage']['memory_increase_mb'] for r in results]
        avg_memory_increase = sum(memory_increases) / len(memory_increases)
        if avg_memory_increase > 100:
            recommendations.append("Significant memory growth per operation. Check for memory leaks.")
        
        # Check thread usage
        max_threads = max(r['peak_usage']['peak_threads'] for r in results)
        if max_threads > 50:
            recommendations.append("High thread count detected. Consider connection pooling optimization.")
        
        if not recommendations:
            recommendations.append("Performance metrics look healthy!")
        
        return recommendations


async def run_performance_analysis():
    """Run comprehensive performance analysis"""
    profiler = SystemProfiler()
    
    print("Starting QaAI Performance Analysis...")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "What are the employment termination procedures in DIFC?",
        "Explain data protection requirements for financial institutions in DIFC",
        "What are the licensing requirements for DFSA regulated entities?",
        "How should companies handle regulatory compliance in DIFC?",
        "What are the corporate governance requirements for DIFC companies?"
    ]
    
    results = []
    
    # Profile assistant queries
    print("\n1. Profiling Assistant Queries...")
    for i, query in enumerate(test_queries, 1):
        print(f"  Query {i}/5...")
        result = await profiler.profile_assistant_query(query)
        results.append(result)
        profiler.metrics.clear()  # Clear metrics for next test
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Profile RAG retrieval
    print("\n2. Profiling RAG Retrieval...")
    for i, query in enumerate(test_queries[:3], 1):  # Test fewer for RAG
        print(f"  RAG Query {i}/3...")
        result = await profiler.profile_rag_retrieval(query)
        results.append(result)
        profiler.metrics.clear()
        await asyncio.sleep(1)
    
    # Generate report
    print("\n3. Generating Performance Report...")
    report = profiler.generate_report(results)
    
    print("\n" + "=" * 50)
    print("PERFORMANCE ANALYSIS REPORT")
    print("=" * 50)
    
    print(f"Total Operations: {report['total_operations']}")
    print(f"Successful: {report['successful_operations']}")
    print(f"Failed: {report['failed_operations']}")
    print(f"\nAverage Duration: {report['average_duration']:.2f}s")
    print(f"Average Memory Usage: {report['average_memory_mb']:.1f}MB")
    print(f"Average CPU Usage: {report['average_cpu_percent']:.1f}%")
    
    print(f"\nPerformance Issues:")
    issues = report['performance_issues']
    print(f"  Slow Operations: {issues['slow_operations']}")
    print(f"  Memory Intensive: {issues['memory_intensive_operations']}")
    print(f"  CPU Intensive: {issues['cpu_intensive_operations']}")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    return report


if __name__ == "__main__":
    asyncio.run(run_performance_analysis())