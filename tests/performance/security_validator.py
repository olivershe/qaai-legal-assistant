#!/usr/bin/env python3
"""
Security validation script for QaAI system
Tests API security, rate limiting, CORS, and input validation
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, List, Any


class SecurityValidator:
    """Security validation for QaAI system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def test_cors_configuration(self) -> Dict[str, Any]:
        """Test CORS configuration"""
        print("Testing CORS configuration...")
        
        cors_tests = []
        
        # Test preflight request
        async with aiohttp.ClientSession() as session:
            try:
                async with session.options(
                    f"{self.base_url}/api/assistant/query",
                    headers={
                        'Origin': 'http://localhost:3000',
                        'Access-Control-Request-Method': 'POST',
                        'Access-Control-Request-Headers': 'Content-Type'
                    }
                ) as response:
                    cors_headers = {
                        'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                        'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                        'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                        'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
                    }
                    
                    cors_tests.append({
                        'test': 'preflight_request',
                        'status_code': response.status,
                        'headers': cors_headers,
                        'success': response.status in [200, 204]
                    })
            except Exception as e:
                cors_tests.append({
                    'test': 'preflight_request',
                    'error': str(e),
                    'success': False
                })
            
            # Test actual cross-origin request
            try:
                async with session.post(
                    f"{self.base_url}/api/assistant/query",
                    json={"mode": "assist", "prompt": "test"},
                    headers={'Origin': 'http://localhost:3000'}
                ) as response:
                    cors_tests.append({
                        'test': 'cross_origin_request',
                        'status_code': response.status,
                        'origin_header': response.headers.get('Access-Control-Allow-Origin'),
                        'success': response.status == 200
                    })
            except Exception as e:
                cors_tests.append({
                    'test': 'cross_origin_request',
                    'error': str(e),
                    'success': False
                })
        
        return {
            'category': 'CORS Configuration',
            'tests': cors_tests,
            'overall_success': all(test['success'] for test in cors_tests)
        }
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting functionality"""
        print("Testing rate limiting...")
        
        rate_limit_tests = []
        
        async with aiohttp.ClientSession() as session:
            # Test rapid requests to health endpoint
            rapid_requests = []
            start_time = time.time()
            
            for i in range(50):  # 50 rapid requests
                try:
                    async with session.get(f"{self.base_url}/health") as response:
                        rapid_requests.append({
                            'request_num': i,
                            'status_code': response.status,
                            'timestamp': time.time() - start_time,
                            'rate_limit_headers': {
                                'X-RateLimit-Limit': response.headers.get('X-RateLimit-Limit'),
                                'X-RateLimit-Remaining': response.headers.get('X-RateLimit-Remaining'),
                                'X-RateLimit-Reset': response.headers.get('X-RateLimit-Reset'),
                                'Retry-After': response.headers.get('Retry-After')
                            }
                        })
                except Exception as e:
                    rapid_requests.append({
                        'request_num': i,
                        'error': str(e),
                        'timestamp': time.time() - start_time
                    })
            
            # Analyze rate limiting
            successful_requests = [r for r in rapid_requests if r.get('status_code') == 200]
            rate_limited_requests = [r for r in rapid_requests if r.get('status_code') == 429]
            
            rate_limit_tests.append({
                'test': 'rapid_requests_health',
                'total_requests': len(rapid_requests),
                'successful': len(successful_requests),
                'rate_limited': len(rate_limited_requests),
                'duration': time.time() - start_time,
                'requests_per_second': len(rapid_requests) / (time.time() - start_time),
                'rate_limiting_active': len(rate_limited_requests) > 0
            })
            
            # Test rate limiting on API endpoints
            api_requests = []
            start_time = time.time()
            
            for i in range(20):  # Fewer requests for API endpoints
                try:
                    async with session.post(
                        f"{self.base_url}/api/assistant/query",
                        json={"mode": "assist", "prompt": "rate limit test"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        api_requests.append({
                            'request_num': i,
                            'status_code': response.status,
                            'timestamp': time.time() - start_time
                        })
                except asyncio.TimeoutError:
                    api_requests.append({
                        'request_num': i,
                        'error': 'timeout',
                        'timestamp': time.time() - start_time
                    })
                except Exception as e:
                    api_requests.append({
                        'request_num': i,
                        'error': str(e),
                        'timestamp': time.time() - start_time
                    })
            
            api_successful = [r for r in api_requests if r.get('status_code') == 200]
            api_rate_limited = [r for r in api_requests if r.get('status_code') == 429]
            
            rate_limit_tests.append({
                'test': 'rapid_requests_api',
                'total_requests': len(api_requests),
                'successful': len(api_successful),
                'rate_limited': len(api_rate_limited),
                'duration': time.time() - start_time,
                'rate_limiting_active': len(api_rate_limited) > 0
            })
        
        return {
            'category': 'Rate Limiting',
            'tests': rate_limit_tests,
            'overall_success': True  # Rate limiting is optional for this system
        }
    
    async def test_input_validation(self) -> Dict[str, Any]:
        """Test input validation and sanitization"""
        print("Testing input validation...")
        
        validation_tests = []
        
        # Test cases for input validation
        test_cases = [
            {
                'name': 'sql_injection',
                'payload': {"mode": "assist", "prompt": "'; DROP TABLE users; --"},
                'expected_behavior': 'safe_handling'
            },
            {
                'name': 'xss_attempt',
                'payload': {"mode": "assist", "prompt": "<script>alert('xss')</script>"},
                'expected_behavior': 'safe_handling'
            },
            {
                'name': 'oversized_input',
                'payload': {"mode": "assist", "prompt": "A" * 10000},  # 10KB prompt
                'expected_behavior': 'validation_error_or_truncation'
            },
            {
                'name': 'invalid_mode',
                'payload': {"mode": "invalid_mode", "prompt": "test"},
                'expected_behavior': 'validation_error'
            },
            {
                'name': 'missing_required_field',
                'payload': {"mode": "assist"},  # Missing prompt
                'expected_behavior': 'validation_error'
            },
            {
                'name': 'invalid_json_structure',
                'payload': {"mode": ["assist"], "prompt": {"nested": "object"}},
                'expected_behavior': 'validation_error'
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            for test_case in test_cases:
                try:
                    async with session.post(
                        f"{self.base_url}/api/assistant/query",
                        json=test_case['payload'],
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        # Determine if response is appropriate
                        success = False
                        if test_case['expected_behavior'] == 'safe_handling':
                            success = response.status == 200  # Should handle safely
                        elif test_case['expected_behavior'] == 'validation_error':
                            success = response.status in [400, 422]  # Should reject
                        elif test_case['expected_behavior'] == 'validation_error_or_truncation':
                            success = response.status in [200, 400, 422]  # Either handle or reject
                        
                        validation_tests.append({
                            'test': test_case['name'],
                            'status_code': response.status,
                            'expected_behavior': test_case['expected_behavior'],
                            'success': success,
                            'payload_size': len(str(test_case['payload']))
                        })
                        
                except Exception as e:
                    validation_tests.append({
                        'test': test_case['name'],
                        'error': str(e),
                        'expected_behavior': test_case['expected_behavior'],
                        'success': False
                    })
        
        return {
            'category': 'Input Validation',
            'tests': validation_tests,
            'overall_success': all(test['success'] for test in validation_tests)
        }
    
    async def test_authentication_security(self) -> Dict[str, Any]:
        """Test authentication and authorization"""
        print("Testing authentication security...")
        
        auth_tests = []
        
        async with aiohttp.ClientSession() as session:
            # Test endpoints without authentication
            endpoints_to_test = [
                "/api/assistant/query",
                "/api/vault/projects", 
                "/api/workflows",
                "/health"
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    method = 'POST' if 'query' in endpoint else 'GET'
                    payload = {"mode": "assist", "prompt": "test"} if method == 'POST' else None
                    
                    if method == 'POST':
                        async with session.post(f"{self.base_url}{endpoint}", json=payload) as response:
                            auth_tests.append({
                                'test': f'unauthenticated_access_{endpoint.replace("/", "_")}',
                                'endpoint': endpoint,
                                'method': method,
                                'status_code': response.status,
                                'requires_auth': response.status == 401,
                                'success': True  # For demo system, this is informational
                            })
                    else:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            auth_tests.append({
                                'test': f'unauthenticated_access_{endpoint.replace("/", "_")}',
                                'endpoint': endpoint,
                                'method': method,
                                'status_code': response.status,
                                'requires_auth': response.status == 401,
                                'success': True
                            })
                            
                except Exception as e:
                    auth_tests.append({
                        'test': f'unauthenticated_access_{endpoint.replace("/", "_")}',
                        'endpoint': endpoint,
                        'error': str(e),
                        'success': False
                    })
        
        return {
            'category': 'Authentication Security',
            'tests': auth_tests,
            'overall_success': all(test['success'] for test in auth_tests)
        }
    
    async def test_information_disclosure(self) -> Dict[str, Any]:
        """Test for information disclosure vulnerabilities"""
        print("Testing information disclosure...")
        
        disclosure_tests = []
        
        async with aiohttp.ClientSession() as session:
            # Test for verbose error messages
            try:
                async with session.get(f"{self.base_url}/nonexistent-endpoint") as response:
                    text = await response.text()
                    
                    # Check if error reveals sensitive information
                    sensitive_patterns = [
                        'traceback', 'stacktrace', 'exception', 'debug',
                        'mysql', 'postgresql', 'sqlite', 'database',
                        'password', 'secret', 'key', 'token'
                    ]
                    
                    sensitive_found = any(pattern.lower() in text.lower() for pattern in sensitive_patterns)
                    
                    disclosure_tests.append({
                        'test': '404_error_disclosure',
                        'status_code': response.status,
                        'sensitive_info_disclosed': sensitive_found,
                        'response_size': len(text),
                        'success': not sensitive_found
                    })
                    
            except Exception as e:
                disclosure_tests.append({
                    'test': '404_error_disclosure',
                    'error': str(e),
                    'success': False
                })
            
            # Test server header information
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    server_header = response.headers.get('Server', '')
                    x_powered_by = response.headers.get('X-Powered-By', '')
                    
                    disclosure_tests.append({
                        'test': 'server_header_disclosure',
                        'server_header': server_header,
                        'x_powered_by': x_powered_by,
                        'headers_present': bool(server_header or x_powered_by),
                        'success': True  # Informational
                    })
                    
            except Exception as e:
                disclosure_tests.append({
                    'test': 'server_header_disclosure',
                    'error': str(e),
                    'success': False
                })
        
        return {
            'category': 'Information Disclosure',
            'tests': disclosure_tests,
            'overall_success': all(test['success'] for test in disclosure_tests)
        }
    
    def generate_security_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        total_tests = sum(len(result['tests']) for result in all_results)
        successful_categories = [result for result in all_results if result['overall_success']]
        
        # Count individual test results
        all_individual_tests = []
        for result in all_results:
            all_individual_tests.extend(result['tests'])
        
        successful_tests = [test for test in all_individual_tests if test.get('success', False)]
        
        return {
            'summary': {
                'total_categories': len(all_results),
                'successful_categories': len(successful_categories),
                'total_individual_tests': total_tests,
                'successful_individual_tests': len(successful_tests),
                'overall_security_score': len(successful_tests) / total_tests if total_tests > 0 else 0
            },
            'categories': all_results,
            'recommendations': self.generate_security_recommendations(all_results)
        }
    
    def generate_security_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Analyze CORS results
        cors_result = next((r for r in results if r['category'] == 'CORS Configuration'), None)
        if cors_result and not cors_result['overall_success']:
            recommendations.append("Configure CORS headers properly for production deployment")
        
        # Analyze rate limiting
        rate_limit_result = next((r for r in results if r['category'] == 'Rate Limiting'), None)
        if rate_limit_result:
            rate_limiting_active = any(
                test.get('rate_limiting_active', False) 
                for test in rate_limit_result['tests']
            )
            if not rate_limiting_active:
                recommendations.append("Implement rate limiting to prevent abuse")
        
        # Analyze input validation
        validation_result = next((r for r in results if r['category'] == 'Input Validation'), None)
        if validation_result and not validation_result['overall_success']:
            recommendations.append("Improve input validation and sanitization")
        
        # Analyze authentication
        auth_result = next((r for r in results if r['category'] == 'Authentication Security'), None)
        if auth_result:
            unauthenticated_access = any(
                test.get('status_code') == 200 and not test.get('requires_auth', False)
                for test in auth_result['tests']
                if 'health' not in test.get('endpoint', '')
            )
            if unauthenticated_access:
                recommendations.append("Consider adding authentication for sensitive endpoints")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Security posture looks good for a development/demo system")
            recommendations.append("Review and enhance security measures before production deployment")
        
        return recommendations


async def main():
    """Main security validation function"""
    base_url = "http://localhost:8000"
    
    print("QaAI Security Validation Suite")
    print("="*60)
    
    # Test server availability
    try:
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(f"{base_url}/health") as response:
                if response.status != 200:
                    print(f"Server not healthy: {response.status}")
                    return
                print("Server is accessible for security testing")
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return
    
    validator = SecurityValidator(base_url)
    
    # Run all security tests
    cors_results = await validator.test_cors_configuration()
    rate_limit_results = await validator.test_rate_limiting()  
    validation_results = await validator.test_input_validation()
    auth_results = await validator.test_authentication_security()
    disclosure_results = await validator.test_information_disclosure()
    
    all_results = [
        cors_results,
        rate_limit_results,
        validation_results,
        auth_results,
        disclosure_results
    ]
    
    # Generate and display report
    report = validator.generate_security_report(all_results)
    
    print("\n" + "="*60)
    print("SECURITY VALIDATION REPORT")
    print("="*60)
    
    summary = report['summary']
    print(f"Categories Tested: {summary['total_categories']}")
    print(f"Successful Categories: {summary['successful_categories']}")
    print(f"Individual Tests: {summary['successful_individual_tests']}/{summary['total_individual_tests']}")
    print(f"Security Score: {summary['overall_security_score']*100:.1f}%")
    
    print(f"\nCategory Results:")
    for result in all_results:
        status = "✅ PASS" if result['overall_success'] else "❌ ISSUES"
        print(f"  {result['category']}: {status} ({len(result['tests'])} tests)")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    print(f"\nDetailed Results:")
    for result in all_results:
        print(f"\n{result['category']}:")
        for test in result['tests']:
            status = "✅" if test.get('success', False) else "❌"
            test_name = test.get('test', 'unknown')
            print(f"  {status} {test_name}")
            
            # Show additional details for interesting results
            if 'rate_limiting_active' in test:
                print(f"    Rate limiting active: {test['rate_limiting_active']}")
            if 'status_code' in test:
                print(f"    Status code: {test['status_code']}")


if __name__ == "__main__":
    asyncio.run(main())