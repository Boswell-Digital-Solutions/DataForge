# GitHub Configuration Guide for DataForge

## Branch Protection Rules

To enable branch protection for the `master` branch, follow these steps:

### Settings → Branches → Branch Protection Rules

1. **Create Rule for `master` branch**

   - Pattern: `master`

2. **Require Status Checks to Pass**

   - ✅ Test Suite (test.yml)
   - ✅ Lint (test.yml)
   - ✅ Security Scanning (security.yml)
   - ✅ Docker Build (docker.yml)
   - Require branches to be up to date before merging: **ON**
   - Require status checks to pass: **ON**

3. **Require Code Review**

   - Require a pull request before merging: **ON**
   - Required approving reviews: **1**
   - Dismiss stale pull request approvals: **ON**
   - Require code review from code owners: **ON**

4. **Require Conversation Resolution**

   - Require all conversations on code to be resolved: **ON**

5. **Require Signed Commits**

   - Require signed commits: **OFF** (Optional, enable for production)

6. **Dismiss Pull Request Reviews**

   - ✅ Enabled

7. **Include Administrators**
   - ✅ Include administrators in restrictions

## GitHub Secrets Configuration

Configure the following secrets in Settings → Secrets and Variables → Actions:

### Required for CI/CD

```
GITHUB_TOKEN: (automatically provided)
```

### Optional - Container Registry

```
# If using private container registry
REGISTRY_USERNAME: your-registry-username
REGISTRY_PASSWORD: your-registry-password
```

### Optional - Deployment

```
# Azure Deployment
AZURE_CREDENTIALS: {"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"..."}
AZURE_RESOURCE_GROUP: your-resource-group

# AWS Deployment
AWS_ACCESS_KEY_ID: your-access-key
AWS_SECRET_ACCESS_KEY: your-secret-key

# Kubernetes Deployment
K8S_CONTEXT: your-k8s-context
K8S_NAMESPACE: production

# Deployment notifications
SLACK_WEBHOOK_URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
DEPLOYMENT_URL: https://your-deployment-url.com
```

### Application Secrets

```
SECRET_KEY: your-production-secret-key
REDIS_URL: redis://your-redis-host:6379/0
DATABASE_URL: postgresql://user:password@host:5432/dbname
VOYAGE_API_KEY: your-voyage-api-key
```

## Workflow Status Badges

Add these to your README.md:

```markdown
[![Test Suite](https://github.com/Boswecw/DataForge/actions/workflows/test.yml/badge.svg)](https://github.com/Boswecw/DataForge/actions/workflows/test.yml)
[![Security Scanning](https://github.com/Boswecw/DataForge/actions/workflows/security.yml/badge.svg)](https://github.com/Boswecw/DataForge/actions/workflows/security.yml)
[![Docker Build](https://github.com/Boswecw/DataForge/actions/workflows/docker.yml/badge.svg)](https://github.com/Boswecw/DataForge/actions/workflows/docker.yml)
```

## Continuous Integration Workflow

### On Push to Master

1. Run test suite (pytest + mypy + coverage)
2. Run security scanning (bandit + safety + CodeQL)
3. Build and push Docker image
4. Scan Docker image for vulnerabilities

### On Pull Request

1. Run test suite
2. Run security checks
3. Build Docker image (don't push)
4. Comment results on PR

### On Release Tag (v*.*.\*)

1. Build and push Docker image with semver tag
2. Run deployment workflow (manual trigger)
3. Notify Slack

## Local Development

### Pre-commit Setup (Optional)

Install pre-commit hooks to run tests locally before committing:

```bash
pip install pre-commit
pre-commit install
```

### Running Tests Locally

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_performance_optimization.py -v

# Type checking
mypy app/ --ignore-missing-imports

# Security scanning
bandit -r app/
safety check
```

## CI/CD Troubleshooting

### Test Failures

1. Check logs: GitHub Actions → Workflows → [Workflow Name]
2. Most common: Missing environment variables
3. Database connection issues (ensure PostgreSQL service running)

### Docker Build Failures

1. Check Dockerfile syntax
2. Verify requirements.txt
3. Check Docker registry credentials in secrets

### Deployment Failures

1. Verify cloud credentials in secrets
2. Check deployment template configuration
3. Review cloud provider error logs

## Repository Structure for CI/CD

```
.github/workflows/
├── test.yml              # Test suite and linting
├── security.yml          # Security scanning
├── docker.yml            # Docker image builds
└── deploy.yml            # Production deployment
```

## Best Practices

1. **Branch Strategy**: Use feature branches, PR for master
2. **Commit Messages**: Follow conventional commits
3. **Test Coverage**: Maintain >70% coverage
4. **Code Reviews**: Require at least 1 approval
5. **Security**: Address critical findings before merge
6. **Deployment**: Test in staging before production

## Monitoring CI/CD

1. **GitHub Actions Dashboard**: github.com/[org]/DataForge/actions
2. **Failed Workflows**: Check failing job logs
3. **Performance**: Monitor workflow execution time
4. **Security Reports**: Review in Security tab
