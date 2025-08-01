"""
Locust performance testing for QaAI Legal Assistant System
Tests RAG retrieval, SSE streaming, and concurrent user scenarios
"""

import json
import time
from locust import HttpUser, task, between
from locust.clients import ResponseContextManager


class QaAIUser(HttpUser):
    """Simulates user interactions with QaAI system"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup user session"""
        self.client.verify = False  # For local testing
        
        # Test health endpoint
        response = self.client.get("/health")
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")
    
    @task(3)
    def test_assistant_query(self):
        """Test Assistant API with DIFC queries"""
        difc_queries = [
            "What are the employment termination procedures in DIFC?",
            "Explain data protection requirements for financial institutions",
            "What are the disclosure requirements for DFSA regulated entities?",
            "How should companies handle employee grievances in DIFC?",
            "What are the licensing requirements for financial services in DIFC?"
        ]
        
        query = self.environment.parsed_options.query if hasattr(self.environment, 'parsed_options') and self.environment.parsed_options.query else difc_queries[0]
        
        payload = {
            "mode": "assist",
            "prompt": query,
            "jurisdiction": "DIFC",
            "model": "gpt-4o-mini"
        }
        
        with self.client.post(
            "/api/assistant/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # Process SSE stream
                content_received = False
                thinking_states = 0
                citations_count = 0
                
                try:
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]  # Remove 'data: ' prefix
                                if data_str.strip() == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if data.get('type') == 'thinking_state':
                                        thinking_states += 1
                                    elif data.get('type') == 'text_chunk':
                                        content_received = True
                                    elif data.get('type') == 'citations':
                                        citations_count += len(data.get('citations', []))
                                except json.JSONDecodeError:
                                    continue
                    
                    if content_received and thinking_states > 0:
                        response.success()
                    else:
                        response.failure(f"Invalid SSE stream: content={content_received}, thinking={thinking_states}")
                        
                except Exception as e:
                    response.failure(f"SSE stream error: {str(e)}")
            else:
                response.failure(f"Assistant query failed: {response.status_code}")
    
    @task(2)
    def test_vault_operations(self):
        """Test Vault API performance"""
        # List projects
        response = self.client.get("/api/vault/projects")
        if response.status_code != 200:
            print(f"Vault projects failed: {response.status_code}")
            return
        
        projects = response.json()
        if projects:
            # Get project details
            project_id = projects[0]['id']
            self.client.get(f"/api/vault/projects/{project_id}")
            
            # List documents in project
            self.client.get(f"/api/vault/projects/{project_id}/documents")
    
    @task(1)
    def test_workflows_list(self):
        """Test Workflows API performance"""
        response = self.client.get("/api/workflows")
        if response.status_code != 200:
            print(f"Workflows list failed: {response.status_code}")
    
    @task(1)
    def test_rag_search(self):
        """Test RAG retrieval performance directly"""
        payload = {
            "query": "DIFC employment law termination procedures",
            "jurisdiction": "DIFC",
            "top_k": 5
        }
        
        response = self.client.post("/api/rag/search", json=payload)
        if response.status_code != 200:
            print(f"RAG search failed: {response.status_code}")


class ConcurrentSSEUser(HttpUser):
    """Tests concurrent SSE streaming scenarios"""
    wait_time = between(0.5, 1)
    
    @task
    def concurrent_sse_stream(self):
        """Test concurrent SSE streams"""
        payload = {
            "mode": "assist", 
            "prompt": "Explain DIFC data protection compliance requirements",
            "model": "gpt-4o-mini"
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/api/assistant/query",
            json=payload,
            stream=True,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                chunks_received = 0
                try:
                    for line in response.iter_lines():
                        if line:
                            chunks_received += 1
                            if chunks_received > 50:  # Limit for load test
                                break
                    
                    duration = time.time() - start_time
                    if duration < 30:  # Should complete within 30 seconds
                        response.success()
                    else:
                        response.failure(f"SSE stream too slow: {duration}s")
                        
                except Exception as e:
                    response.failure(f"Concurrent SSE error: {str(e)}")
            else:
                response.failure(f"Concurrent SSE failed: {response.status_code}")


class RAGPerformanceUser(HttpUser):
    """Focused RAG retrieval performance testing"""
    wait_time = between(0.1, 0.5)
    
    @task
    def rag_retrieval_speed(self):
        """Test RAG retrieval speed with various queries"""
        queries = [
            "employment termination DIFC",
            "data protection financial services",
            "DFSA licensing requirements", 
            "regulatory compliance obligations",
            "corporate governance standards"
        ]
        
        query = queries[hash(str(time.time())) % len(queries)]
        
        start_time = time.time()
        response = self.client.post("/api/rag/search", json={
            "query": query,
            "jurisdiction": "DIFC", 
            "top_k": 10
        })
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            results = response.json()
            if len(results.get('documents', [])) > 0 and duration < 2.0:
                # RAG should return results within 2 seconds
                pass
            else:
                print(f"RAG slow or empty: {duration}s, {len(results.get('documents', []))} docs")
        else:
            print(f"RAG retrieval failed: {response.status_code}")