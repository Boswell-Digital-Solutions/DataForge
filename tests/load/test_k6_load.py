"""
Load testing suite using k6 (Python client wrapper).
Tests API performance under high concurrency with detailed metrics.

Installation:
    pip install k6
    
Usage:
    python -m pytest tests/load/test_k6_load.py -v
    
    Or with k6 directly:
    k6 run tests/load/k6_test.js
"""

import pytest
import requests
import time
import random
import string
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LOAD_TESTS") != "1",
    reason="Load tests require an explicit RUN_LOAD_TESTS=1 opt-in and a running local API server.",
)


@dataclass
class RequestMetrics:
    """Track metrics for a single request type."""
    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
    
    @property
    def p99_response_time(self) -> float:
        """Calculate 99th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
    
    @property
    def max_response_time(self) -> float:
        """Get maximum response time."""
        return max(self.response_times) if self.response_times else 0
    
    
    @property
    def min_response_time(self) -> float:
        """Get minimum response time."""
        return min(self.response_times) if self.response_times else 0


class LoadTestUser:
    """Simulates a single user performing API operations."""
    
    def __init__(self, user_id: int, base_url: str):
        self.user_id = user_id
        self.base_url = base_url
        self.username = f"loadtest_{user_id}_{int(time.time()*1000)}"
        self.email = f"{self.username}@loadtest.local"
        self.password = "LoadTestPass123!"
        self.token = None
        self.session = requests.Session()
        self.metrics: Dict[str, RequestMetrics] = {}
        self.project_ids: List[str] = []
        self.diligence_ids: List[str] = []
    
    def register_and_login(self) -> bool:
        """Register user and obtain authentication token."""
        try:
            # Register
            register_url = f"{self.base_url}/api/auth/register"
            register_response = self.session.post(
                register_url,
                json={
                    "email": self.email,
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )
            
            if register_response.status_code != 200:
                return False
            
            # Login
            login_url = f"{self.base_url}/api/auth/login"
            login_response = self.session.post(
                login_url,
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )
            
            if login_response.status_code == 200:
                self.token = login_response.json().get("access_token")
                return True
            
            return False
        
        except Exception as e:
            print(f"❌ User {self.user_id}: Registration failed - {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def track_request(self, endpoint: str, status_code: int, response_time: float, error: Optional[str] = None):
        """Track request metrics."""
        if endpoint not in self.metrics:
            self.metrics[endpoint] = RequestMetrics(name=endpoint)
        
        metric = self.metrics[endpoint]
        metric.total_requests += 1
        metric.response_times.append(response_time)
        
        if status_code < 400:
            metric.successful_requests += 1
        else:
            metric.failed_requests += 1
            if error:
                metric.error_messages.append(error)
    
    def make_request(self, method: str, endpoint: str, json_data: Optional[dict] = None) -> Tuple[int, float]:
        """Make HTTP request and return status code and response time."""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = self.get_headers()
            
            start_time = time.time()
            
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=json_data, headers=headers, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=json_data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                return 0, 0
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            self.track_request(endpoint, response.status_code, response_time)
            
            return response.status_code, response_time
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.track_request(endpoint, 0, response_time, str(e))
            return 0, response_time
    
    def execute_workload(self, num_operations: int = 10):
        """Execute typical user workload."""
        for _ in range(num_operations):
            operation = random.choice([
                self.get_projects,
                self.create_project,
                self.search_projects,
                self.create_diligence,
            ])
            
            try:
                operation()
                time.sleep(random.uniform(0.1, 0.5))  # Small delay between operations
            except Exception as e:
                print(f"❌ User {self.user_id}: Operation failed - {e}")
    
    def get_projects(self):
        """GET /api/projects"""
        self.make_request("GET", "/api/projects")
    
    def create_project(self):
        """POST /api/projects"""
        project_data = {
            "name": f"Load Test {int(time.time()*1000)}",
            "industry": random.choice(["Technology", "Healthcare", "Finance"]),
            "stage": random.choice(["Seed", "Series A", "Series B"]),
        }
        
        status, _ = self.make_request("POST", "/api/projects", project_data)
        
        if status == 200:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/projects",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    projects = response.json()
                    if projects:
                        self.project_ids.append(projects[0].get("id"))
            except:
                pass
    
    def search_projects(self):
        """GET /api/search"""
        query = random.choice(["tech", "ai", "data", "test"])
        self.make_request("GET", f"/api/search?q={query}")
    
    def create_diligence(self):
        """POST /api/diligence"""
        if not self.project_ids:
            return
        
        project_id = random.choice(self.project_ids)
        diligence_data = {
            "project_id": project_id,
            "review_type": random.choice(["technical", "financial"]),
        }
        
        status, _ = self.make_request("POST", "/api/diligence", diligence_data)
        
        if status == 200:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/diligence",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    diligences = response.json()
                    if diligences:
                        self.diligence_ids.append(diligences[0].get("id"))
            except:
                pass


class LoadTestRunner:
    """Orchestrates load testing with multiple concurrent users."""
    
    def __init__(self, base_url: str, num_users: int, duration_seconds: int):
        self.base_url = base_url
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.all_metrics: Dict[str, RequestMetrics] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def aggregate_metrics(self, user: LoadTestUser):
        """Aggregate metrics from a user."""
        for endpoint, metrics in user.metrics.items():
            if endpoint not in self.all_metrics:
                self.all_metrics[endpoint] = RequestMetrics(name=endpoint)
            
            agg = self.all_metrics[endpoint]
            agg.total_requests += metrics.total_requests
            agg.successful_requests += metrics.successful_requests
            agg.failed_requests += metrics.failed_requests
            agg.response_times.extend(metrics.response_times)
            agg.error_messages.extend(metrics.error_messages)
    
    def run(self) -> Dict[str, RequestMetrics]:
        """Run load test with concurrent users."""
        print(f"\n{'='*60}")
        print(f"LOAD TEST: {self.num_users} users for {self.duration_seconds}s")
        print(f"{'='*60}\n")
        
        self.start_time = time.time()
        users = []
        
        # Initialize users
        for i in range(self.num_users):
            user = LoadTestUser(i, self.base_url)
            if user.register_and_login():
                users.append(user)
            else:
                print(f"⚠️  Failed to initialize user {i}")
        
        print(f"✅ Initialized {len(users)} users\n")
        
        # Run load test
        with ThreadPoolExecutor(max_workers=min(self.num_users, 50)) as executor:
            futures = []
            start = time.time()
            
            # Submit tasks until duration expires
            while time.time() - start < self.duration_seconds:
                for user in users:
                    future = executor.submit(
                        user.execute_workload,
                        num_operations=random.randint(3, 7)
                    )
                    futures.append(future)
                
                # Check for completion every second
                time.sleep(1)
            
            # Wait for remaining tasks
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Task failed: {e}")
        
        self.end_time = time.time()
        
        # Aggregate metrics
        for user in users:
            self.aggregate_metrics(user)
        
        return self.all_metrics
    
    def print_report(self):
        """Print performance report."""
        print(f"\n{'='*80}")
        print("LOAD TEST REPORT")
        print(f"{'='*80}\n")
        
        total_duration = self.end_time - self.start_time
        print(f"Duration: {total_duration:.1f}s")
        print(f"Concurrent Users: {self.num_users}\n")
        
        print(f"{'Endpoint':<30} {'Requests':<12} {'Success Rate':<15} {'Avg (ms)':<12} {'P95 (ms)':<12}")
        print("-" * 80)
        
        total_requests = 0
        total_successful = 0
        
        for endpoint, metrics in sorted(self.all_metrics.items()):
            total_requests += metrics.total_requests
            total_successful += metrics.successful_requests
            
            print(f"{endpoint:<30} {metrics.total_requests:<12} "
                  f"{metrics.success_rate*100:>6.1f}%       {metrics.avg_response_time:>8.1f}  "
                  f"{metrics.p95_response_time:>8.1f}")
        
        print("-" * 80)
        overall_success_rate = total_successful / total_requests if total_requests > 0 else 0
        print(f"{'TOTAL':<30} {total_requests:<12} {overall_success_rate*100:>6.1f}%\n")
        
        # Throughput
        throughput = total_requests / total_duration
        print(f"Throughput: {throughput:.1f} requests/second")
        
        # Check for errors
        has_errors = any(metrics.failed_requests > 0 for metrics in self.all_metrics.values())
        
        if has_errors:
            print(f"\n⚠️  ERRORS DETECTED:")
            for endpoint, metrics in self.all_metrics.items():
                if metrics.failed_requests > 0:
                    print(f"  {endpoint}: {metrics.failed_requests} failures")
                    for error in metrics.error_messages[:3]:
                        print(f"    - {error}")


@pytest.mark.load
class TestLoadPerformance:
    """Pytest-compatible load testing suite."""
    
    def test_50_concurrent_users_30_seconds(self):
        """Test with 50 concurrent users for 30 seconds."""
        runner = LoadTestRunner(
            base_url="http://localhost:8001",
            num_users=50,
            duration_seconds=30
        )
        
        metrics = runner.run()
        runner.print_report()
        
        # Assertions
        assert len(metrics) > 0, "No metrics collected"
        
        for endpoint, m in metrics.items():
            assert m.successful_requests > 0, f"{endpoint}: No successful requests"
            assert m.success_rate >= 0.95, f"{endpoint}: Success rate too low ({m.success_rate*100:.1f}%)"
    
    def test_100_concurrent_users_60_seconds(self):
        """Test with 100 concurrent users for 60 seconds."""
        runner = LoadTestRunner(
            base_url="http://localhost:8001",
            num_users=100,
            duration_seconds=60
        )
        
        metrics = runner.run()
        runner.print_report()
        
        # Assertions
        assert len(metrics) > 0, "No metrics collected"
        
        for endpoint, m in metrics.items():
            assert m.success_rate >= 0.90, f"{endpoint}: Success rate too low"
    
    def test_response_time_benchmarks(self):
        """Test that response times meet benchmarks."""
        runner = LoadTestRunner(
            base_url="http://localhost:8001",
            num_users=25,
            duration_seconds=15
        )
        
        metrics = runner.run()
        runner.print_report()
        
        # Response time benchmarks (in ms)
        benchmarks = {
            "/api/projects": 500,
            "/api/search": 2000,
            "/api/diligence": 1000,
        }
        
        for endpoint, max_time in benchmarks.items():
            if endpoint in metrics:
                m = metrics[endpoint]
                assert m.avg_response_time < max_time, \
                    f"{endpoint}: avg {m.avg_response_time:.0f}ms > {max_time}ms"


if __name__ == "__main__":
    # Example standalone usage
    runner = LoadTestRunner(
        base_url="http://localhost:8001",
        num_users=50,
        duration_seconds=30
    )
    
    runner.run()
    runner.print_report()
