#!/usr/bin/env python3
"""
Performance Analysis Script for Telegram Bot
Analyzes the codebase for performance bottlenecks and provides optimization recommendations.
"""

import os
import sys
import ast
import time
import asyncio
import logging
import subprocess
from typing import Dict, List, Tuple, Any
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Analyzes Python code for performance issues"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.issues = []
        self.metrics = {
            'total_files': 0,
            'total_lines': 0,
            'large_files': [],
            'complex_functions': [],
            'async_issues': [],
            'import_issues': [],
            'memory_issues': []
        }
        
    def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze the entire codebase for performance issues"""
        logger.info("Starting performance analysis...")
        
        python_files = list(self.root_path.rglob("*.py"))
        self.metrics['total_files'] = len(python_files)
        
        for file_path in python_files:
            self._analyze_file(file_path)
            
        return self._generate_report()
        
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                return
                
            lines = content.split('\n')
            self.metrics['total_lines'] += len(lines)
            
            # Check file size
            if len(lines) > 500:
                self.metrics['large_files'].append({
                    'file': str(file_path),
                    'lines': len(lines),
                    'recommendation': 'Consider breaking into smaller modules'
                })
                
            # Parse AST
            try:
                tree = ast.parse(content)
                self._analyze_ast(file_path, tree, content)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            
    def _analyze_ast(self, file_path: Path, tree: ast.AST, content: str):
        """Analyze AST for performance issues"""
        visitor = PerformanceVisitor(file_path, content)
        visitor.visit(tree)
        
        # Collect issues
        self.metrics['complex_functions'].extend(visitor.complex_functions)
        self.metrics['async_issues'].extend(visitor.async_issues)
        self.metrics['import_issues'].extend(visitor.import_issues)
        self.metrics['memory_issues'].extend(visitor.memory_issues)
        
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'summary': {
                'total_files': self.metrics['total_files'],
                'total_lines': self.metrics['total_lines'],
                'issues_found': len(self.metrics['large_files']) + 
                              len(self.metrics['complex_functions']) +
                              len(self.metrics['async_issues']) +
                              len(self.metrics['import_issues']) +
                              len(self.metrics['memory_issues'])
            },
            'issues': self.metrics,
            'recommendations': self._generate_recommendations(),
            'optimization_impact': self._estimate_optimization_impact()
        }
        
        return report
        
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Large files
        if self.metrics['large_files']:
            recommendations.append({
                'category': 'Code Structure',
                'issue': f"Found {len(self.metrics['large_files'])} large files",
                'recommendation': 'Break large files into smaller, focused modules',
                'impact': 'High'
            })
            
        # Complex functions
        if self.metrics['complex_functions']:
            recommendations.append({
                'category': 'Function Complexity',
                'issue': f"Found {len(self.metrics['complex_functions'])} complex functions",
                'recommendation': 'Refactor complex functions into smaller, testable units',
                'impact': 'Medium'
            })
            
        # Async issues
        if self.metrics['async_issues']:
            recommendations.append({
                'category': 'Async Programming',
                'issue': f"Found {len(self.metrics['async_issues'])} async performance issues",
                'recommendation': 'Optimize async operations and add connection pooling',
                'impact': 'High'
            })
            
        # Import issues
        if self.metrics['import_issues']:
            recommendations.append({
                'category': 'Import Optimization',
                'issue': f"Found {len(self.metrics['import_issues'])} import optimization opportunities",
                'recommendation': 'Optimize imports and use lazy loading where appropriate',
                'impact': 'Medium'
            })
            
        return recommendations
        
    def _estimate_optimization_impact(self) -> Dict[str, Any]:
        """Estimate the impact of optimizations"""
        total_issues = (len(self.metrics['large_files']) + 
                       len(self.metrics['complex_functions']) +
                       len(self.metrics['async_issues']) +
                       len(self.metrics['import_issues']) +
                       len(self.metrics['memory_issues']))
                       
        if total_issues == 0:
            return {
                'performance_improvement': '0%',
                'memory_usage_reduction': '0%',
                'startup_time_improvement': '0%',
                'maintenance_score_improvement': '0%'
            }
            
        # Estimate improvements based on issue types
        async_improvement = len(self.metrics['async_issues']) * 15  # 15% per async issue
        memory_improvement = len(self.metrics['memory_issues']) * 10  # 10% per memory issue
        startup_improvement = len(self.metrics['import_issues']) * 5  # 5% per import issue
        
        return {
            'performance_improvement': f"{min(async_improvement, 50)}%",
            'memory_usage_reduction': f"{min(memory_improvement, 30)}%",
            'startup_time_improvement': f"{min(startup_improvement, 20)}%",
            'maintenance_score_improvement': f"{min(total_issues * 5, 40)}%"
        }

class PerformanceVisitor(ast.NodeVisitor):
    """AST visitor for performance analysis"""
    
    def __init__(self, file_path: Path, content: str):
        self.file_path = file_path
        self.content = content
        self.complex_functions = []
        self.async_issues = []
        self.import_issues = []
        self.memory_issues = []
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions"""
        # Check function complexity
        if self._calculate_complexity(node) > 10:
            self.complex_functions.append({
                'file': str(self.file_path),
                'function': node.name,
                'complexity': self._calculate_complexity(node),
                'lines': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 'Unknown',
                'recommendation': 'Consider breaking into smaller functions'
            })
            
        # Check async function issues
        if node.decorator_list:
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'async':
                    # Check for blocking operations in async functions
                    if self._has_blocking_operations(node):
                        self.async_issues.append({
                            'file': str(self.file_path),
                            'function': node.name,
                            'issue': 'Blocking operations in async function',
                            'recommendation': 'Use asyncio.to_thread() or async alternatives'
                        })
                        
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Analyze async function definitions"""
        # Check for blocking operations
        if self._has_blocking_operations(node):
            self.async_issues.append({
                'file': str(self.file_path),
                'function': node.name,
                'issue': 'Blocking operations in async function',
                'recommendation': 'Use asyncio.to_thread() or async alternatives'
            })
            
        self.generic_visit(node)
        
    def visit_Import(self, node: ast.Import):
        """Analyze import statements"""
        for alias in node.names:
            if alias.name.startswith('requests') or alias.name.startswith('urllib'):
                self.import_issues.append({
                    'file': str(self.file_path),
                    'line': node.lineno,
                    'issue': f'Using {alias.name} in async context',
                    'recommendation': 'Use httpx or aiohttp for async HTTP requests'
                })
                
        self.generic_visit(node)
        
    def visit_Call(self, node: ast.Call):
        """Analyze function calls for performance issues"""
        if isinstance(node.func, ast.Attribute):
            # Check for potential memory leaks
            if node.func.attr in ['read', 'readlines']:
                self.memory_issues.append({
                    'file': str(self.file_path),
                    'line': node.lineno,
                    'issue': 'Large file read operation',
                    'recommendation': 'Use streaming or chunked reading for large files'
                })
                
        self.generic_visit(node)
        
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                complexity += 1
            elif isinstance(child, ast.While):
                complexity += 1
            elif isinstance(child, ast.For):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
                
        return complexity
        
    def _has_blocking_operations(self, node: ast.FunctionDef) -> bool:
        """Check for blocking operations in function"""
        blocking_operations = [
            'time.sleep', 'requests.get', 'requests.post', 'urllib.request',
            'open', 'file.read', 'file.write'
        ]
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    full_name = f"{getattr(child.func.value, 'id', '')}.{child.func.attr}"
                    if any(op in full_name for op in blocking_operations):
                        return True
                        
        return False

async def analyze_dependencies():
    """Analyze Python dependencies for performance impact"""
    logger.info("Analyzing dependencies...")
    
    try:
        # Get installed packages
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], 
                              capture_output=True, text=True)
        packages = json.loads(result.stdout)
        
        performance_impact = {
            'heavy_packages': [],
            'optimization_suggestions': []
        }
        
        for package in packages:
            name = package['name'].lower()
            version = package['version']
            
            # Check for known heavy packages
            heavy_packages = {
                'pandas': 'Consider using polars or pyarrow for better performance',
                'numpy': 'Already optimized, ensure using latest version',
                'matplotlib': 'Consider using plotly or bokeh for web applications',
                'scipy': 'Already optimized, ensure using latest version',
                'tensorflow': 'Consider using torch or onnx for inference',
                'flask': 'Consider using fastapi for better performance',
                'django': 'Consider using fastapi for microservices'
            }
            
            if name in heavy_packages:
                performance_impact['heavy_packages'].append({
                    'name': name,
                    'version': version,
                    'suggestion': heavy_packages[name]
                })
                
        return performance_impact
        
    except Exception as e:
        logger.error(f"Error analyzing dependencies: {e}")
        return {'heavy_packages': [], 'optimization_suggestions': []}

def print_report(report: Dict[str, Any]):
    """Print formatted performance report"""
    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS REPORT")
    print("="*80)
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Total files analyzed: {report['summary']['total_files']}")
    print(f"   Total lines of code: {report['summary']['total_lines']:,}")
    print(f"   Issues found: {report['summary']['issues_found']}")
    
    # Issues breakdown
    print(f"\n🔍 ISSUES BREAKDOWN:")
    print(f"   Large files: {len(report['issues']['large_files'])}")
    print(f"   Complex functions: {len(report['issues']['complex_functions'])}")
    print(f"   Async issues: {len(report['issues']['async_issues'])}")
    print(f"   Import issues: {len(report['issues']['import_issues'])}")
    print(f"   Memory issues: {len(report['issues']['memory_issues'])}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"   [{rec['category']}] {rec['issue']}")
        print(f"      💡 {rec['recommendation']} (Impact: {rec['impact']})")
        
    # Optimization impact
    impact = report['optimization_impact']
    print(f"\n🚀 ESTIMATED OPTIMIZATION IMPACT:")
    print(f"   Performance improvement: {impact['performance_improvement']}")
    print(f"   Memory usage reduction: {impact['memory_usage_reduction']}")
    print(f"   Startup time improvement: {impact['startup_time_improvement']}")
    print(f"   Maintenance score improvement: {impact['maintenance_score_improvement']}")
    
    # Top issues
    if report['issues']['large_files']:
        print(f"\n📁 LARGEST FILES:")
        for file_info in sorted(report['issues']['large_files'], 
                              key=lambda x: x['lines'], reverse=True)[:5]:
            print(f"   {file_info['file']}: {file_info['lines']} lines")
            
    if report['issues']['complex_functions']:
        print(f"\n🔧 MOST COMPLEX FUNCTIONS:")
        for func_info in sorted(report['issues']['complex_functions'], 
                              key=lambda x: x['complexity'], reverse=True)[:5]:
            print(f"   {func_info['function']} in {func_info['file']}: complexity {func_info['complexity']}")
            
    print("\n" + "="*80)

async def main():
    """Main analysis function"""
    logger.info("Starting comprehensive performance analysis...")
    
    # Analyze codebase
    analyzer = PerformanceAnalyzer()
    report = analyzer.analyze_codebase()
    
    # Analyze dependencies
    deps_report = await analyze_dependencies()
    report['dependencies'] = deps_report
    
    # Print report
    print_report(report)
    
    # Save detailed report
    with open('performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)
        
    logger.info("Performance analysis complete. Detailed report saved to performance_report.json")
    
    return report

if __name__ == '__main__':
    asyncio.run(main())