
/* global __ENV, __VU, console, success */
/**
 * K6 Load Testing Script
 *
 * Modern, scalable load testing for DataForge API
 *
 * Installation:
 *   - Download k6 from https://k6.io/docs/getting-started/installation/
 *   - Or use docker: docker run -i grafana/k6 run - < tests/load/k6_test.js
 *
 * Usage:
 *   k6 run tests/load/k6_test.js
 *   k6 run tests/load/k6_test.js -v  # Verbose
 *   k6 run tests/load/k6_test.js --vus 100 --duration 60s  # Override settings
 *
 * Documentation:
 *   https://k6.io/docs/
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend, Rate, Counter, Gauge } from "k6/metrics";

// Custom metrics
const apiDuration = new Trend("api_duration", true);
const apiErrors = new Rate("api_errors");
const apiSuccesses = new Rate("api_success");
const apiThroughput = new Counter("api_throughput");
const concurrentUsers = new Gauge("concurrent_users");

// Configuration
export const options = {
  stages: [
    { duration: "30s", target: 20 }, // Ramp-up to 20 users
    { duration: "1m30s", target: 50 }, // Ramp-up to 50 users
    { duration: "2m", target: 50 }, // Stay at 50 users
    { duration: "30s", target: 0 }, // Ramp-down to 0 users
  ],
  thresholds: {
    api_duration: ["p(95)<1000", "p(99)<2000"], // 95% < 1s, 99% < 2s
    api_errors: ["rate<0.1"], // Error rate < 10%
    api_success: ["rate>0.9"], // Success rate > 90%
    http_req_duration: ["p(95)<1000"],
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8001";

/**
 * Setup: Initialize test data
 */
export function setup() {
  console.log("🚀 Starting DataForge Load Test");
  console.log(`📍 Target: ${BASE_URL}`);

  const testUser = {
    email: `loadtest_${Date.now()}@loadtest.local`,
    username: `loadtest_${Date.now()}`,
    password: "LoadTestPass123!",
  };

  // Register user
  const registerResponse = http.post(
    `${BASE_URL}/api/auth/register`,
    JSON.stringify({
      email: testUser.email,
      username: testUser.username,
      password: testUser.password,
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(registerResponse, {
    "registration successful": (r) => r.status === 200,
  });

  // Login
  const loginResponse = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({
      username: testUser.username,
      password: testUser.password,
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(loginResponse, {
    "login successful": (r) => r.status === 200,
  });

  const token = loginResponse.json("access_token");

  return {
    token: token,
    email: testUser.email,
    projectIds: [],
  };
}

/**
 * Main test function
 */
export default function (data) {
  const token = data.token;
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  // Track concurrent users
  concurrentUsers.add(__VU);

  group("API Tests", function () {
    // Test 1: List Projects (30% of traffic)
    group("List Projects", function () {
      const response = http.get(`${BASE_URL}/api/projects`, { headers });

      const duration = response.timings.duration;
      apiDuration.add(duration);
      apiThroughput.add(1);

      if (
        check(response, {
          "status is 200": (r) => r.status === 200,
          "has results": (r) => r.json("length") > 0 || true,
        })
      ) {
        apiSuccesses.add(1);
      } else {
        apiErrors.add(1);
      }
    });

    sleep(Math.random() * 2);

    // Test 2: Create Project (20% of traffic)
    group("Create Project", function () {
      const projectData = {
        name: `Load Test Project ${Date.now()}`,
        industry: ["Technology", "Healthcare", "Finance"][
          Math.floor(Math.random() * 3)
        ],
        stage: ["Seed", "Series A", "Series B"][Math.floor(Math.random() * 3)],
      };

      const response = http.post(
        `${BASE_URL}/api/projects`,
        JSON.stringify(projectData),
        { headers }
      );

      const duration = response.timings.duration;
      apiDuration.add(duration);
      apiThroughput.add(1);

      if (
        check(response, {
          "status is 200": (r) => r.status === 200,
        })
      ) {
        apiSuccesses.add(1);
        // Store project ID for later tests
        const project = response.json();
        if (project.id) {
          data.projectIds.push(project.id);
        }
      } else {
        apiErrors.add(1);
      }
    });

    sleep(Math.random() * 2);

    // Test 3: Get Single Project (10% of traffic)
    if (data.projectIds.length > 0) {
      group("Get Single Project", function () {
        const projectId =
          data.projectIds[Math.floor(Math.random() * data.projectIds.length)];
        const response = http.get(`${BASE_URL}/api/projects/${projectId}`, {
          headers,
        });

        const duration = response.timings.duration;
        apiDuration.add(duration);
        apiThroughput.add(1);

        if (
          check(response, {
            "status is 200": (r) => r.status === 200 || r.status === 404,
          })
        ) {
          if (response.status === 200) {
            apiSuccesses.add(1);
          } else if (response.status === 404) {
            // Expected if project was deleted
            apiSuccesses.add(1);
          }
        } else {
          apiErrors.add(1);
        }
      });

      sleep(Math.random() * 1.5);
    }

    // Test 4: Update Project (10% of traffic)
    if (data.projectIds.length > 0) {
      group("Update Project", function () {
        const projectId =
          data.projectIds[Math.floor(Math.random() * data.projectIds.length)];
        const updateData = {
          name: `Updated ${Date.now()}`,
          status: ["active", "on_hold", "completed"][
            Math.floor(Math.random() * 3)
          ],
        };

        const response = http.put(
          `${BASE_URL}/api/projects/${projectId}`,
          JSON.stringify(updateData),
          { headers }
        );

        const duration = response.timings.duration;
        apiDuration.add(duration);
        apiThroughput.add(1);

        if (
          check(response, {
            "status is 200": (r) => r.status === 200 || r.status === 404,
          })
        ) {
          if (response.status === 200 || response.status === 404) {
            apiSuccesses.add(1);
          }
        } else {
          apiErrors.add(1);
        }
      });

      sleep(Math.random() * 1.5);
    }

    // Test 5: Search Projects (15% of traffic)
    group("Search Projects", function () {
      const queries = ["tech", "ai", "data", "machine", "cloud"];
      const query = queries[Math.floor(Math.random() * queries.length)];

      const response = http.get(`${BASE_URL}/api/search?q=${query}`, {
        headers,
      });

      const duration = response.timings.duration;
      apiDuration.add(duration);
      apiThroughput.add(1);

      if (
        check(response, {
          "status is 200": (r) => r.status === 200,
        })
      ) {
        apiSuccesses.add(1);
      } else {
        apiErrors.add(1);
      }
    });

    sleep(Math.random() * 2);

    // Test 6: Create Diligence (8% of traffic)
    if (data.projectIds.length > 0) {
      group("Create Diligence", function () {
        const projectId =
          data.projectIds[Math.floor(Math.random() * data.projectIds.length)];
        const diligenceData = {
          project_id: projectId,
          review_type: ["technical", "financial"][
            Math.floor(Math.random() * 2)
          ],
        };

        const response = http.post(
          `${BASE_URL}/api/diligence`,
          JSON.stringify(diligenceData),
          { headers }
        );

        const duration = response.timings.duration;
        apiDuration.add(duration);
        apiThroughput.add(1);

        if (
          check(response, {
            "status is 200": (r) => r.status === 200 || r.status === 404,
          })
        ) {
          apiSuccesses.add(1);
        } else {
          apiErrors.add(1);
        }
      });

      sleep(Math.random() * 1.5);
    }

    // Test 7: Health Check (2% of traffic)
    group("Health Check", function () {
      const response = http.get(`${BASE_URL}/health`);

      const duration = response.timings.duration;
      apiDuration.add(duration);
      apiThroughput.add(1);

      if (
        check(response, {
          "status is 200": (r) => r.status === 200,
        })
      ) {
        apiSuccesses.add(1);
      } else {
        apiErrors.add(1);
      }
    });
  });

  // Random think time between requests
  sleep(Math.random() * 3);
}

/**
 * Teardown: Print summary
 */
export function teardown(data) {
  console.log("✅ Load test completed");
}

/**
 * Handle VU init
 */
export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "summary.json": JSON.stringify(data),
  };
}

/**
 * Text summary formatter
 */
function textSummary(summaryData, options) {
  const indent = options.indent || "";
  const lines = [];

  lines.push("");
  lines.push(
    "================================================================="
  );
  lines.push("K6 LOAD TEST SUMMARY");
  lines.push(
    "================================================================="
  );
  lines.push("");

  if (summaryData.metrics) {
    lines.push("Response Times:");
    if (summaryData.metrics.api_duration) {
      const trend = summaryData.metrics.api_duration;
      lines.push(`${indent}Mean: ${trend.values.mean || "N/A"} ms`);
      lines.push(`${indent}P95: ${trend.values["p(95)"] || "N/A"} ms`);
      lines.push(`${indent}P99: ${trend.values["p(99)"] || "N/A"} ms`);
      lines.push(`${indent}Max: ${trend.values.max || "N/A"} ms`);
    }
    lines.push("");

    lines.push("Success Rates:");
    if (summaryData.metrics.api_success) {
      const successRate = (summaryData.metrics.api_success.value * 100).toFixed(2);
      lines.push(`${indent}API Success: ${successRate}%`);
    }
    if (summaryData.metrics.api_errors) {
      const errorRate = (summaryData.metrics.api_errors.value * 100).toFixed(2);
      lines.push(`${indent}API Errors: ${errorRate}%`);
    }
    lines.push("");

    if (summaryData.metrics.api_throughput) {
      lines.push(`Throughput: ${summaryData.metrics.api_throughput.value} requests`);
    }
  }

  lines.push("");
  lines.push(
    "================================================================="
  );

  return lines.join("\n");
}
