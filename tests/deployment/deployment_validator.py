#!/usr/bin/env python3
"""
Deployment script validator for QaAI system
Tests deployment scripts, backup procedures, and monitoring setup
"""

import os
import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Any, Optional


class DeploymentValidator:
    """Validates deployment scripts and procedures"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = []
    
    def test_deployment_script(self) -> Dict[str, Any]:
        """Test deployment script functionality"""
        print("Testing deployment script...")
        
        script_tests = []
        deploy_script = self.project_root / "scripts/deploy.sh"
        
        if not deploy_script.exists():
            return {
                'category': 'Deployment Script',
                'tests': [{'test': 'script_exists', 'success': False, 'error': 'deploy.sh not found'}],
                'overall_success': False
            }
        
        # Test script syntax
        try:
            result = subprocess.run(
                ['bash', '-n', str(deploy_script)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            script_tests.append({
                'test': 'syntax_check',
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            })
            
        except subprocess.TimeoutExpired:
            script_tests.append({
                'test': 'syntax_check',
                'success': False,
                'error': 'Script syntax check timed out'
            })
        except Exception as e:
            script_tests.append({
                'test': 'syntax_check',
                'success': False,
                'error': str(e)
            })
        
        # Test help output
        try:
            result = subprocess.run(
                ['bash', str(deploy_script), '--help'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root)
            )
            
            has_usage = 'Usage:' in result.stdout or 'usage:' in result.stdout.lower()
            has_options = '--' in result.stdout
            
            script_tests.append({
                'test': 'help_output',
                'success': has_usage,
                'has_usage': has_usage,
                'has_options': has_options,
                'output_length': len(result.stdout)
            })
            
        except subprocess.TimeoutExpired:
            script_tests.append({
                'test': 'help_output',
                'success': False,
                'error': 'Help command timed out'
            })
        except Exception as e:
            script_tests.append({
                'test': 'help_output',
                'success': False,
                'error': str(e)
            })
        
        # Test dry-run functionality (with modified log path)
        try:
            # Create a temporary log file in the project directory
            temp_log = self.project_root / "temp_deploy.log"
            
            # Modify environment to use local log file
            env = os.environ.copy()
            env['LOG_FILE'] = str(temp_log)
            
            result = subprocess.run(
                ['bash', str(deploy_script), '--dry-run', 'staging'],
                capture_output=True,
                text=True,
                timeout=60,  # Longer timeout for full dry run
                cwd=str(self.project_root),
                env=env
            )
            
            # Clean up temp log file if created
            if temp_log.exists():
                temp_log.unlink()
            
            script_tests.append({
                'test': 'dry_run',
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'has_output': len(result.stdout) > 0,
                'error': result.stderr if result.returncode != 0 else None
            })
            
        except subprocess.TimeoutExpired:
            script_tests.append({
                'test': 'dry_run',
                'success': False,
                'error': 'Dry run timed out'
            })
        except Exception as e:
            script_tests.append({
                'test': 'dry_run',
                'success': False,
                'error': str(e)
            })
        
        return {
            'category': 'Deployment Script',
            'tests': script_tests,
            'overall_success': all(test['success'] for test in script_tests)
        }
    
    def test_setup_script(self) -> Dict[str, Any]:
        """Test setup script functionality"""
        print("Testing setup script...")
        
        script_tests = []
        setup_script = self.project_root / "scripts/setup.sh"
        
        if not setup_script.exists():
            return {
                'category': 'Setup Script',
                'tests': [{'test': 'script_exists', 'success': False, 'error': 'setup.sh not found'}],
                'overall_success': False
            }
        
        # Test script syntax
        try:
            result = subprocess.run(
                ['bash', '-n', str(setup_script)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            script_tests.append({
                'test': 'syntax_check',
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            })
            
        except Exception as e:
            script_tests.append({
                'test': 'syntax_check',
                'success': False,
                'error': str(e)
            })
        
        # Check for key setup functions
        try:
            with open(setup_script, 'r') as f:
                content = f.read()
            
            has_docker_check = 'docker' in content.lower()
            has_env_setup = '.env' in content
            has_permissions = 'chmod' in content or 'chown' in content
            
            script_tests.append({
                'test': 'setup_functions',
                'success': has_docker_check and has_env_setup,
                'has_docker_check': has_docker_check,
                'has_env_setup': has_env_setup,
                'has_permissions': has_permissions
            })
            
        except Exception as e:
            script_tests.append({
                'test': 'setup_functions',
                'success': False,
                'error': str(e)
            })
        
        return {
            'category': 'Setup Script',
            'tests': script_tests,
            'overall_success': all(test['success'] for test in script_tests)
        }
    
    def test_health_check_script(self) -> Dict[str, Any]:
        """Test health check script functionality"""
        print("Testing health check script...")
        
        script_tests = []
        health_script = self.project_root / "scripts/health-check.sh"
        
        if not health_script.exists():
            return {
                'category': 'Health Check Script',
                'tests': [{'test': 'script_exists', 'success': False, 'error': 'health-check.sh not found'}],
                'overall_success': False
            }
        
        # Test script syntax
        try:
            result = subprocess.run(
                ['bash', '-n', str(health_script)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            script_tests.append({
                'test': 'syntax_check',
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            })
            
        except Exception as e:
            script_tests.append({
                'test': 'syntax_check',
                'success': False,
                'error': str(e)
            })
        
        # Test health check execution (should work with current running system)
        try:
            result = subprocess.run(
                ['bash', str(health_script), '--verbose'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root)
            )
            
            # Health check might fail if services aren't running, but script should execute
            script_executed = result.returncode is not None
            has_output = len(result.stdout) > 0 or len(result.stderr) > 0
            
            script_tests.append({
                'test': 'health_check_execution',
                'success': script_executed and has_output,
                'return_code': result.returncode,
                'has_output': has_output,
                'output_length': len(result.stdout) + len(result.stderr)
            })
            
        except subprocess.TimeoutExpired:
            script_tests.append({
                'test': 'health_check_execution',
                'success': False,
                'error': 'Health check timed out'
            })
        except Exception as e:
            script_tests.append({
                'test': 'health_check_execution',
                'success': False,
                'error': str(e)
            })
        
        return {
            'category': 'Health Check Script',
            'tests': script_tests,
            'overall_success': all(test['success'] for test in script_tests)
        }
    
    def test_backup_procedures(self) -> Dict[str, Any]:
        """Test backup and recovery procedures"""
        print("Testing backup procedures...")
        
        backup_tests = []
        
        # Check for backup directory structure
        docker_backup_dir = self.project_root / "docker/backup"
        if docker_backup_dir.exists():
            backup_tests.append({
                'test': 'backup_directory_exists',
                'success': True,
                'path': str(docker_backup_dir)
            })
            
            # Look for backup scripts
            backup_scripts = list(docker_backup_dir.glob("*.sh"))
            backup_tests.append({
                'test': 'backup_scripts_present',
                'success': len(backup_scripts) > 0,
                'script_count': len(backup_scripts),
                'scripts': [s.name for s in backup_scripts]
            })
            
        else:
            backup_tests.append({
                'test': 'backup_directory_exists',
                'success': False,
                'error': 'Docker backup directory not found'
            })
        
        # Check backup configuration in docker-compose.prod.yml
        prod_compose = self.project_root / "docker-compose.prod.yml"
        if prod_compose.exists():
            try:
                with open(prod_compose, 'r') as f:
                    content = f.read()
                
                has_backup_service = 'backup:' in content
                has_backup_volumes = 'backup' in content and 'volumes:' in content
                
                backup_tests.append({
                    'test': 'backup_service_configured',
                    'success': has_backup_service,
                    'has_backup_service': has_backup_service,
                    'has_backup_volumes': has_backup_volumes
                })
                
            except Exception as e:
                backup_tests.append({
                    'test': 'backup_service_configured',
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'category': 'Backup Procedures',
            'tests': backup_tests,
            'overall_success': all(test['success'] for test in backup_tests)
        }
    
    def test_monitoring_configuration(self) -> Dict[str, Any]:
        """Test monitoring stack configuration"""
        print("Testing monitoring configuration...")
        
        monitoring_tests = []
        
        # Check Prometheus configuration
        prometheus_config = self.project_root / "docker/prometheus/prometheus.yml"
        if prometheus_config.exists():
            try:
                with open(prometheus_config, 'r') as f:
                    content = f.read()
                
                has_scrape_configs = 'scrape_configs:' in content
                has_qaai_targets = 'qaai-api' in content
                
                monitoring_tests.append({
                    'test': 'prometheus_config',
                    'success': has_scrape_configs and has_qaai_targets,
                    'has_scrape_configs': has_scrape_configs,
                    'has_qaai_targets': has_qaai_targets
                })
                
            except Exception as e:
                monitoring_tests.append({
                    'test': 'prometheus_config',
                    'success': False,
                    'error': str(e)
                })
        else:
            monitoring_tests.append({
                'test': 'prometheus_config',
                'success': False,
                'error': 'Prometheus config not found'
            })
        
        # Check Grafana datasources
        grafana_datasources = self.project_root / "docker/grafana/datasources"
        if grafana_datasources.exists():
            datasource_files = list(grafana_datasources.glob("*.yml"))
            monitoring_tests.append({
                'test': 'grafana_datasources',
                'success': len(datasource_files) > 0,
                'datasource_count': len(datasource_files),
                'datasources': [f.name for f in datasource_files]
            })
        else:
            monitoring_tests.append({
                'test': 'grafana_datasources',
                'success': False,
                'error': 'Grafana datasources directory not found'
            })
        
        # Check monitoring services in production compose
        prod_compose = self.project_root / "docker-compose.prod.yml"
        if prod_compose.exists():
            try:
                with open(prod_compose, 'r') as f:
                    content = f.read()
                
                has_prometheus = 'prometheus:' in content
                has_grafana = 'grafana:' in content
                has_loki = 'loki:' in content
                
                monitoring_tests.append({
                    'test': 'monitoring_services',
                    'success': has_prometheus and has_grafana,
                    'has_prometheus': has_prometheus,
                    'has_grafana': has_grafana,
                    'has_loki': has_loki
                })
                
            except Exception as e:
                monitoring_tests.append({
                    'test': 'monitoring_services',
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'category': 'Monitoring Configuration',
            'tests': monitoring_tests,
            'overall_success': all(test['success'] for test in monitoring_tests)
        }
    
    def generate_deployment_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive deployment readiness report"""
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
                'deployment_readiness_score': len(successful_tests) / len(all_tests) if all_tests else 0
            },
            'categories': all_results,
            'recommendations': self._generate_deployment_recommendations(all_results)
        }
    
    def _generate_deployment_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate deployment recommendations"""
        recommendations = []
        
        # Check script functionality
        for result in results:
            if not result['overall_success']:
                category = result['category']
                recommendations.append(f"Fix issues in {category} before deployment")
        
        # Specific recommendations based on test results
        deployment_result = next((r for r in results if r['category'] == 'Deployment Script'), None)
        if deployment_result:
            dry_run_test = next((t for t in deployment_result['tests'] if t.get('test') == 'dry_run'), None)
            if dry_run_test and not dry_run_test['success']:
                recommendations.append("Deployment script dry-run failed - review script permissions and paths")
        
        backup_result = next((r for r in results if r['category'] == 'Backup Procedures'), None)
        if backup_result and not backup_result['overall_success']:
            recommendations.append("Set up backup procedures before production deployment")
        
        monitoring_result = next((r for r in results if r['category'] == 'Monitoring Configuration'), None)
        if monitoring_result and not monitoring_result['overall_success']:
            recommendations.append("Configure monitoring stack for production visibility")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Deployment scripts and procedures are ready!")
            recommendations.append("Test deployment in staging environment before production")
            recommendations.append("Ensure proper SSL certificates and DNS configuration")
        
        return recommendations


def main():
    """Main deployment validation function"""
    project_root = "/Users/ollieshewan/Desktop/QaAI - DIFC/Main"
    
    print("QaAI Deployment Validation Suite")
    print("="*50)
    
    validator = DeploymentValidator(project_root)
    
    # Run all validation tests
    deployment_results = validator.test_deployment_script()
    setup_results = validator.test_setup_script()
    health_results = validator.test_health_check_script()
    backup_results = validator.test_backup_procedures()
    monitoring_results = validator.test_monitoring_configuration()
    
    all_results = [
        deployment_results,
        setup_results,
        health_results,
        backup_results,
        monitoring_results
    ]
    
    # Generate report
    report = validator.generate_deployment_report(all_results)
    
    print("\\n" + "="*50)
    print("DEPLOYMENT VALIDATION REPORT")
    print("="*50)
    
    summary = report['summary']
    print(f"Categories Tested: {summary['total_categories']}")
    print(f"Successful Categories: {summary['successful_categories']}")
    print(f"Individual Tests: {summary['successful_tests']}/{summary['total_tests']}")
    print(f"Deployment Readiness Score: {summary['deployment_readiness_score']*100:.1f}%")
    
    print(f"\\nCategory Results:")
    for result in all_results:
        status = "✅ READY" if result['overall_success'] else "❌ ISSUES"
        print(f"  {result['category']}: {status} ({len(result['tests'])} tests)")
    
    print(f"\\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    print(f"\\nDetailed Results:")
    for result in all_results:
        print(f"\\n{result['category']}:")
        for test in result['tests']:
            status = "✅" if test.get('success', False) else "❌"
            test_name = test.get('test', 'unknown')
            print(f"  {status} {test_name}")
            if 'error' in test:
                print(f"    Error: {test['error']}")
    
    return report


if __name__ == "__main__":
    main()