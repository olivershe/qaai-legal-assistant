#!/usr/bin/env python3
"""
Docker configuration and deployment validator for QaAI system
Tests Docker configurations, validates services, and checks deployment readiness
"""

import os
import yaml
import json
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path


class DockerValidator:
    """Validates Docker configuration and deployment setup"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = []
        
    def validate_docker_compose_files(self) -> Dict[str, Any]:
        """Validate Docker Compose configurations"""
        print("Validating Docker Compose configurations...")
        
        compose_tests = []
        
        # Test main docker-compose.yml
        dev_compose_path = self.project_root / "docker-compose.yml"
        if dev_compose_path.exists():
            try:
                with open(dev_compose_path, 'r') as f:
                    dev_config = yaml.safe_load(f)
                
                # Validate structure
                required_sections = ['services', 'networks', 'volumes']
                missing_sections = [s for s in required_sections if s not in dev_config]
                
                # Validate services
                services = dev_config.get('services', {})
                required_services = ['qaai-api', 'qaai-web', 'redis']
                missing_services = [s for s in required_services if s not in services]
                
                compose_tests.append({
                    'file': 'docker-compose.yml',
                    'valid_yaml': True,
                    'missing_sections': missing_sections,
                    'missing_services': missing_services,
                    'total_services': len(services),
                    'success': len(missing_sections) == 0 and len(missing_services) == 0
                })
                
            except yaml.YAMLError as e:
                compose_tests.append({
                    'file': 'docker-compose.yml',
                    'valid_yaml': False,
                    'error': str(e),
                    'success': False
                })
        else:
            compose_tests.append({
                'file': 'docker-compose.yml',
                'exists': False,
                'success': False
            })
        
        # Test production docker-compose.prod.yml
        prod_compose_path = self.project_root / "docker-compose.prod.yml"
        if prod_compose_path.exists():
            try:
                with open(prod_compose_path, 'r') as f:
                    prod_config = yaml.safe_load(f)
                
                services = prod_config.get('services', {})
                compose_tests.append({
                    'file': 'docker-compose.prod.yml',
                    'valid_yaml': True,
                    'total_services': len(services),
                    'has_healthchecks': self._count_healthchecks(services),
                    'has_resource_limits': self._count_resource_limits(services),
                    'success': True
                })
                
            except yaml.YAMLError as e:
                compose_tests.append({
                    'file': 'docker-compose.prod.yml',
                    'valid_yaml': False,
                    'error': str(e),
                    'success': False
                })
        else:
            compose_tests.append({
                'file': 'docker-compose.prod.yml',
                'exists': False,
                'success': False
            })
        
        return {
            'category': 'Docker Compose Configuration',
            'tests': compose_tests,
            'overall_success': all(test['success'] for test in compose_tests)
        }
    
    def validate_dockerfiles(self) -> Dict[str, Any]:
        """Validate Dockerfile configurations"""
        print("Validating Dockerfiles...")
        
        dockerfile_tests = []
        
        # Check for required Dockerfiles
        expected_dockerfiles = [
            'docker/Dockerfile.api',
            'docker/Dockerfile.web'
        ]
        
        for dockerfile_path in expected_dockerfiles:
            full_path = self.project_root / dockerfile_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    
                    # Validate Dockerfile content
                    has_from = 'FROM' in content
                    has_workdir = 'WORKDIR' in content
                    has_copy = 'COPY' in content
                    has_cmd = 'CMD' in content or 'ENTRYPOINT' in content
                    has_healthcheck = 'HEALTHCHECK' in content
                    has_user = 'USER' in content
                    has_multistage = content.count('FROM') > 1
                    
                    dockerfile_tests.append({
                        'file': dockerfile_path,
                        'exists': True,
                        'has_from': has_from,
                        'has_workdir': has_workdir,
                        'has_copy': has_copy,
                        'has_cmd': has_cmd,
                        'has_healthcheck': has_healthcheck,
                        'has_user': has_user,
                        'multistage_build': has_multistage,
                        'size_bytes': len(content),
                        'success': has_from and has_workdir and has_copy and has_cmd
                    })
                    
                except Exception as e:
                    dockerfile_tests.append({
                        'file': dockerfile_path,
                        'exists': True,
                        'error': str(e),
                        'success': False
                    })
            else:
                dockerfile_tests.append({
                    'file': dockerfile_path,
                    'exists': False,
                    'success': False
                })
        
        return {
            'category': 'Dockerfile Configuration',
            'tests': dockerfile_tests,
            'overall_success': all(test['success'] for test in dockerfile_tests)
        }
    
    def validate_docker_support_files(self) -> Dict[str, Any]:
        """Validate Docker support files (nginx.conf, prometheus.yml, etc.)"""
        print("Validating Docker support files...")
        
        support_tests = []
        
        # Check nginx configuration
        nginx_path = self.project_root / "docker/nginx.conf"
        if nginx_path.exists():
            try:
                with open(nginx_path, 'r') as f:
                    nginx_content = f.read()
                
                has_server_block = 'server {' in nginx_content
                has_gzip = 'gzip on' in nginx_content
                has_security_headers = 'X-Frame-Options' in nginx_content
                has_api_proxy = '/api/' in nginx_content
                
                support_tests.append({
                    'file': 'docker/nginx.conf',
                    'has_server_block': has_server_block,
                    'has_gzip': has_gzip,
                    'has_security_headers': has_security_headers,
                    'has_api_proxy': has_api_proxy,
                    'success': has_server_block and has_api_proxy
                })
                
            except Exception as e:
                support_tests.append({
                    'file': 'docker/nginx.conf',
                    'error': str(e),
                    'success': False
                })
        else:
            support_tests.append({
                'file': 'docker/nginx.conf',
                'exists': False,
                'success': False
            })
        
        # Check Prometheus configuration
        prometheus_path = self.project_root / "docker/prometheus/prometheus.yml"
        if prometheus_path.exists():
            try:
                with open(prometheus_path, 'r') as f:
                    prometheus_config = yaml.safe_load(f)
                
                has_scrape_configs = 'scrape_configs' in prometheus_config
                scrape_jobs = len(prometheus_config.get('scrape_configs', []))
                has_qaai_jobs = any(
                    job.get('job_name', '').startswith('qaai-') 
                    for job in prometheus_config.get('scrape_configs', [])
                )
                
                support_tests.append({
                    'file': 'docker/prometheus/prometheus.yml',
                    'valid_yaml': True,
                    'has_scrape_configs': has_scrape_configs,
                    'scrape_jobs': scrape_jobs,
                    'has_qaai_jobs': has_qaai_jobs,
                    'success': has_scrape_configs and scrape_jobs > 0
                })
                
            except yaml.YAMLError as e:
                support_tests.append({
                    'file': 'docker/prometheus/prometheus.yml',
                    'valid_yaml': False,
                    'error': str(e),
                    'success': False
                })
        else:
            support_tests.append({
                'file': 'docker/prometheus/prometheus.yml',
                'exists': False,
                'success': False
            })
        
        return {
            'category': 'Docker Support Files',
            'tests': support_tests,
            'overall_success': all(test['success'] for test in support_tests)
        }
    
    def validate_environment_configuration(self) -> Dict[str, Any]:
        """Validate environment configuration files"""
        print("Validating environment configuration...")
        
        env_tests = []
        
        # Check .env.example
        env_example_path = self.project_root / ".env.example"
        if env_example_path.exists():
            try:
                with open(env_example_path, 'r') as f:
                    env_content = f.read()
                
                # Check for required environment variables
                required_vars = [
                    'OPENAI_API_KEY',
                    'ANTHROPIC_API_KEY',
                    'APP_ENV',
                    'DB_URL',
                    'CORS_ORIGINS'
                ]
                
                missing_vars = [var for var in required_vars if var not in env_content]
                
                env_tests.append({
                    'file': '.env.example',
                    'missing_vars': missing_vars,
                    'total_vars': len(env_content.split('\n')),
                    'success': len(missing_vars) == 0
                })
                
            except Exception as e:
                env_tests.append({
                    'file': '.env.example',
                    'error': str(e),
                    'success': False
                })
        else:
            env_tests.append({
                'file': '.env.example',
                'exists': False,
                'success': False
            })
        
        return {
            'category': 'Environment Configuration',
            'tests': env_tests,
            'overall_success': all(test['success'] for test in env_tests)
        }
    
    def validate_deployment_scripts(self) -> Dict[str, Any]:
        """Validate deployment and management scripts"""
        print("Validating deployment scripts...")
        
        script_tests = []
        
        # Check for deployment scripts
        expected_scripts = [
            'scripts/deploy.sh',
            'scripts/setup.sh',
            'scripts/health-check.sh'
        ]
        
        for script_path in expected_scripts:
            full_path = self.project_root / script_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        script_content = f.read()
                    
                    # Check script characteristics
                    has_shebang = script_content.startswith('#!')
                    has_docker_commands = 'docker' in script_content.lower()
                    is_executable = os.access(full_path, os.X_OK)
                    
                    script_tests.append({
                        'file': script_path,
                        'has_shebang': has_shebang,
                        'has_docker_commands': has_docker_commands,
                        'is_executable': is_executable,
                        'size_bytes': len(script_content),
                        'success': has_shebang and is_executable
                    })
                    
                except Exception as e:
                    script_tests.append({
                        'file': script_path,
                        'error': str(e),
                        'success': False
                    })
            else:
                script_tests.append({
                    'file': script_path,
                    'exists': False,
                    'success': False
                })
        
        return {
            'category': 'Deployment Scripts',
            'tests': script_tests,
            'overall_success': all(test['success'] for test in script_tests)
        }
    
    def _count_healthchecks(self, services: Dict) -> int:
        """Count services with healthcheck configuration"""
        return sum(1 for service in services.values() if 'healthcheck' in service)
    
    def _count_resource_limits(self, services: Dict) -> int:
        """Count services with resource limits"""
        return sum(1 for service in services.values() if 'deploy' in service)
    
    def generate_docker_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive Docker deployment report"""
        total_categories = len(all_results)
        successful_categories = [r for r in all_results if r['overall_success']]
        
        # Count individual tests
        all_tests = []
        for result in all_results:
            all_tests.extend(result['tests'])
        
        successful_tests = [t for t in all_tests if t.get('success', False)]
        
        return {
            'summary': {
                'total_categories': total_categories,
                'successful_categories': len(successful_categories),
                'total_tests': len(all_tests),
                'successful_tests': len(successful_tests),
                'docker_readiness_score': len(successful_tests) / len(all_tests) if all_tests else 0
            },
            'categories': all_results,
            'recommendations': self._generate_docker_recommendations(all_results)
        }
    
    def _generate_docker_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate Docker deployment recommendations"""
        recommendations = []
        
        # Check Docker Compose
        compose_result = next((r for r in results if r['category'] == 'Docker Compose Configuration'), None)
        if compose_result and not compose_result['overall_success']:
            recommendations.append("Fix Docker Compose configuration issues before deployment")
        
        # Check Dockerfiles
        dockerfile_result = next((r for r in results if r['category'] == 'Dockerfile Configuration'), None)
        if dockerfile_result:
            missing_dockerfiles = [t for t in dockerfile_result['tests'] if not t.get('exists', True)]
            if missing_dockerfiles:
                recommendations.append("Create missing Dockerfiles for complete containerization")
        
        # Check support files
        support_result = next((r for r in results if r['category'] == 'Docker Support Files'), None)
        if support_result and not support_result['overall_success']:
            recommendations.append("Configure missing Docker support files (nginx, prometheus)")
        
        # Check environment
        env_result = next((r for r in results if r['category'] == 'Environment Configuration'), None)
        if env_result and not env_result['overall_success']:
            recommendations.append("Complete environment variable configuration")
        
        # Check scripts
        script_result = next((r for r in results if r['category'] == 'Deployment Scripts'), None)
        if script_result and not script_result['overall_success']:
            recommendations.append("Ensure deployment scripts are executable and complete")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Docker configuration looks good!")
            recommendations.append("Test deployment in a staging environment before production")
        
        return recommendations


def create_deployment_test_script():
    """Create a test script for Docker deployment"""
    test_script = '''#!/bin/bash
# QaAI Docker Deployment Test Script
# Tests Docker deployment in a safe environment

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "QaAI Docker Deployment Test"
echo "=========================="

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Validate configurations
echo "\\nValidating Docker configurations..."
docker-compose config --quiet
if [ $? -eq 0 ]; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    exit 1
fi

# Test build (without running)
echo "\\nTesting Docker builds..."
docker-compose build --no-cache qaai-api
if [ $? -eq 0 ]; then
    echo "✅ API Docker build successful"
else
    echo "❌ API Docker build failed"
    exit 1
fi

docker-compose build --no-cache qaai-web
if [ $? -eq 0 ]; then
    echo "✅ Web Docker build successful"
else
    echo "❌ Web Docker build failed"
    exit 1
fi

# Test basic services startup
echo "\\nTesting service startup..."
docker-compose up -d redis
sleep 5

# Check if Redis is running
if docker-compose ps redis | grep -q "Up"; then
    echo "✅ Redis service started successfully"
    docker-compose down
else
    echo "❌ Redis service failed to start"
    docker-compose down
    exit 1
fi

echo "\\n✅ All Docker deployment tests passed!"
echo "Ready for full deployment testing"
'''
    
    return test_script


def main():
    """Main Docker validation function"""
    project_root = "/Users/ollieshewan/Desktop/QaAI - DIFC/Main"
    
    print("QaAI Docker Deployment Validation")
    print("="*50)
    
    validator = DockerValidator(project_root)
    
    # Run all validation tests
    compose_results = validator.validate_docker_compose_files()
    dockerfile_results = validator.validate_dockerfiles()
    support_results = validator.validate_docker_support_files()
    env_results = validator.validate_environment_configuration()
    script_results = validator.validate_deployment_scripts()
    
    all_results = [
        compose_results,
        dockerfile_results,
        support_results,
        env_results,
        script_results
    ]
    
    # Generate report
    report = validator.generate_docker_report(all_results)
    
    print("\\n" + "="*50)
    print("DOCKER DEPLOYMENT VALIDATION REPORT")
    print("="*50)
    
    summary = report['summary']
    print(f"Categories Tested: {summary['total_categories']}")
    print(f"Successful Categories: {summary['successful_categories']}")
    print(f"Individual Tests: {summary['successful_tests']}/{summary['total_tests']}")
    print(f"Docker Readiness Score: {summary['docker_readiness_score']*100:.1f}%")
    
    print(f"\\nCategory Results:")
    for result in all_results:
        status = "✅ READY" if result['overall_success'] else "❌ ISSUES"
        print(f"  {result['category']}: {status} ({len(result['tests'])} tests)")
    
    print(f"\\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    # Create deployment test script
    test_script_path = Path(project_root) / "tests/deployment/docker_test.sh"
    test_script_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_script_path, 'w') as f:
        f.write(create_deployment_test_script())
    
    # Make script executable
    os.chmod(test_script_path, 0o755)
    
    print(f"\\n✅ Created Docker test script: {test_script_path}")
    
    return report


if __name__ == "__main__":
    main()