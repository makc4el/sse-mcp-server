#!/usr/bin/env python3
"""
Test runner for SSE MCP Server
"""

import pytest
import sys
import os
from pathlib import Path


def run_tests():
    """Run all tests with coverage reporting"""
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    print("🧪 Running SSE MCP Server Tests")
    print("=" * 50)
    
    # Test arguments
    args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=main",  # Coverage for main module
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov",  # HTML coverage report
        "test_unit.py",  # Unit tests
        "test_integration.py",  # Integration tests
    ]
    
    # Run tests
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        
    return exit_code


def run_unit_tests():
    """Run only unit tests"""
    print("🔬 Running Unit Tests Only")
    print("=" * 30)
    
    args = ["-v", "--tb=short", "test_unit.py"]
    return pytest.main(args)


def run_integration_tests():
    """Run only integration tests"""
    print("🔗 Running Integration Tests Only")
    print("=" * 35)
    
    args = ["-v", "--tb=short", "test_integration.py"]
    return pytest.main(args)


def run_with_coverage():
    """Run tests with detailed coverage"""
    print("📈 Running Tests with Coverage")
    print("=" * 35)
    
    args = [
        "-v",
        "--cov=main",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80",  # Fail if coverage below 80%
        "test_unit.py",
        "test_integration.py"
    ]
    
    return pytest.main(args)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "unit":
            exit_code = run_unit_tests()
        elif command == "integration":
            exit_code = run_integration_tests()
        elif command == "coverage":
            exit_code = run_with_coverage()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: unit, integration, coverage")
            exit_code = 1
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)

