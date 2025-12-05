#!/usr/bin/env python3
"""
Forge Ecosystem Testing Suite
Tests RAG Pipeline, DataForge, and Rake components
"""

import requests
import json
import time
from typing import Dict, Any, List
import sys

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class ForgeEcosystemTester:
    """Comprehensive testing for Forge Ecosystem components"""

    def __init__(self, dataforge_url: str = "http://localhost:8001"):
        self.dataforge_url = dataforge_url
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

    def print_test(self, name: str, status: str, message: str = ""):
        """Print test result"""
        if status == "PASS":
            symbol = "✅"
            color = Colors.GREEN
            self.results["passed"].append(name)
        elif status == "FAIL":
            symbol = "❌"
            color = Colors.RED
            self.results["failed"].append(name)
        else:  # SKIP
            symbol = "⏭️"
            color = Colors.YELLOW
            self.results["skipped"].append(name)

        print(f"{symbol} {color}{name}{Colors.END}", end="")
        if message:
            print(f" - {message}")
        else:
            print()

    def test_dataforge_health(self) -> bool:
        """Test DataForge server health check"""
        try:
            response = requests.get(f"{self.dataforge_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_test("DataForge Health Check", "PASS",
                              f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.print_test("DataForge Health Check", "FAIL",
                              f"Status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.print_test("DataForge Health Check", "FAIL",
                          "Server not running")
            return False
        except Exception as e:
            self.print_test("DataForge Health Check", "FAIL", str(e))
            return False

    def test_semantic_search(self) -> bool:
        """Test semantic search endpoint"""
        try:
            payload = {
                "query": "machine learning algorithms",
                "limit": 5
            }
            response = requests.post(
                f"{self.dataforge_url}/api/search/semantic",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                self.print_test("Semantic Search", "PASS",
                              f"Returned {len(results)} results in {data.get('query_time_ms', 0)}ms")
                return True
            else:
                self.print_test("Semantic Search", "FAIL",
                              f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Semantic Search", "FAIL", str(e))
            return False

    def test_keyword_search(self, skip_if_sqlite: bool = True) -> bool:
        """Test keyword (BM25) search endpoint"""
        try:
            payload = {
                "query": "machine learning",
                "limit": 5
            }
            response = requests.post(
                f"{self.dataforge_url}/api/search/keyword",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                self.print_test("Keyword Search (BM25)", "PASS",
                              f"Returned {len(results)} results in {data.get('query_time_ms', 0)}ms")
                return True
            elif response.status_code == 501:  # Not Implemented (SQLite)
                if skip_if_sqlite:
                    self.print_test("Keyword Search (BM25)", "SKIP",
                                  "Requires PostgreSQL (using SQLite)")
                    return True
                else:
                    self.print_test("Keyword Search (BM25)", "FAIL",
                                  "Not available with SQLite")
                    return False
            else:
                self.print_test("Keyword Search (BM25)", "FAIL",
                              f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Keyword Search (BM25)", "FAIL", str(e))
            return False

    def test_hybrid_search(self, skip_if_sqlite: bool = True) -> bool:
        """Test hybrid search endpoint"""
        try:
            payload = {
                "query": "machine learning",
                "limit": 5
            }
            response = requests.post(
                f"{self.dataforge_url}/api/search/hybrid",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                self.print_test("Hybrid Search (RRF)", "PASS",
                              f"Returned {len(results)} results in {data.get('query_time_ms', 0)}ms")
                return True
            elif response.status_code == 501:  # Not Implemented (SQLite)
                if skip_if_sqlite:
                    self.print_test("Hybrid Search (RRF)", "SKIP",
                                  "Requires PostgreSQL (using SQLite)")
                    return True
                else:
                    self.print_test("Hybrid Search (RRF)", "FAIL",
                                  "Not available with SQLite")
                    return False
            else:
                self.print_test("Hybrid Search (RRF)", "FAIL",
                              f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Hybrid Search (RRF)", "FAIL", str(e))
            return False

    def test_database_connectivity(self) -> bool:
        """Test database connectivity"""
        try:
            # Try to access any endpoint that requires DB
            response = requests.get(f"{self.dataforge_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                db_status = data.get("database", "unknown")
                if db_status == "connected" or data.get("status") == "healthy":
                    self.print_test("Database Connectivity", "PASS",
                                  f"Database: {db_status}")
                    return True
                else:
                    self.print_test("Database Connectivity", "FAIL",
                                  f"Database: {db_status}")
                    return False
            else:
                self.print_test("Database Connectivity", "FAIL",
                              "Cannot determine status")
                return False
        except Exception as e:
            self.print_test("Database Connectivity", "FAIL", str(e))
            return False

    def test_api_endpoints_exist(self) -> bool:
        """Test that RAG API endpoints exist"""
        endpoints = [
            "/api/search/semantic",
            "/api/search/keyword",
            "/api/search/hybrid"
        ]

        all_exist = True
        for endpoint in endpoints:
            try:
                # Use HEAD request or empty POST to check existence
                response = requests.post(
                    f"{self.dataforge_url}{endpoint}",
                    json={"query": "test", "limit": 1},
                    timeout=5
                )
                # 200, 422, or 501 means endpoint exists
                if response.status_code in [200, 422, 501]:
                    self.print_test(f"API Endpoint {endpoint}", "PASS",
                                  f"Exists (status: {response.status_code})")
                else:
                    self.print_test(f"API Endpoint {endpoint}", "FAIL",
                                  f"Status: {response.status_code}")
                    all_exist = False
            except Exception as e:
                self.print_test(f"API Endpoint {endpoint}", "FAIL", str(e))
                all_exist = False

        return all_exist

    def print_summary(self):
        """Print test summary"""
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["skipped"])

        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}Test Summary{Colors.END}")
        print(f"{'='*70}")

        print(f"\n{Colors.GREEN}✅ Passed: {len(self.results['passed'])}{Colors.END}")
        print(f"{Colors.RED}❌ Failed: {len(self.results['failed'])}{Colors.END}")
        print(f"{Colors.YELLOW}⏭️  Skipped: {len(self.results['skipped'])}{Colors.END}")
        print(f"{Colors.BOLD}Total: {total}{Colors.END}\n")

        if self.results["failed"]:
            print(f"{Colors.RED}Failed Tests:{Colors.END}")
            for test in self.results["failed"]:
                print(f"  - {test}")

        if self.results["skipped"]:
            print(f"\n{Colors.YELLOW}Skipped Tests:{Colors.END}")
            for test in self.results["skipped"]:
                print(f"  - {test}")

        print(f"\n{Colors.BOLD}Overall Status: ", end="")
        if len(self.results["failed"]) == 0:
            print(f"{Colors.GREEN}✅ ALL TESTS PASSED{Colors.END}")
            return 0
        else:
            print(f"{Colors.RED}❌ SOME TESTS FAILED{Colors.END}")
            return 1

def main():
    """Run all ecosystem tests"""
    tester = ForgeEcosystemTester()

    tester.print_header("Forge Ecosystem Testing Suite")
    print(f"{Colors.BLUE}Testing RAG Pipeline Components{Colors.END}\n")

    # Test 1: DataForge Server
    tester.print_header("1. DataForge Server Health")
    if not tester.test_dataforge_health():
        print(f"\n{Colors.RED}❌ DataForge server is not running. Please start it first:{Colors.END}")
        print(f"   cd DataForge && source venv/bin/activate && uvicorn app.main:app --port 8001\n")
        return 1

    # Test 2: Database
    tester.print_header("2. Database Connectivity")
    tester.test_database_connectivity()

    # Test 3: API Endpoints
    tester.print_header("3. RAG API Endpoints")
    tester.test_api_endpoints_exist()

    # Test 4: Search Functionality
    tester.print_header("4. Search Functionality")
    tester.test_semantic_search()
    tester.test_keyword_search(skip_if_sqlite=True)
    tester.test_hybrid_search(skip_if_sqlite=True)

    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
