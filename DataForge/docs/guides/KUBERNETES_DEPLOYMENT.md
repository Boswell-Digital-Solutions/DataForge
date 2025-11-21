# Kubernetes Deployment Guide for DataForge

## Overview

This guide provides step-by-step instructions for deploying DataForge to a Kubernetes cluster in production.

**Files Included:**

- `k8s/dataforge.yaml` - Core application deployment (15+ manifests)
- `k8s/ingress.yaml` - Ingress controller configuration (TLS, rate limiting)
- `prometheus.yml` - Prometheus metrics scrape configuration
- `prometheus-rules.yml` - Alert rules for production monitoring
- `nginx.conf` - Nginx reverse proxy configuration
- `.env.production` - Production environment variables

---

## Prerequisites

### Required Tools

- `kubectl` 1.24+ ([Install Guide](https://kubernetes.io/docs/tasks/tools/))
- `helm` 3.0+ (optional, for package management)
- A Kubernetes cluster 1.24+ (EKS, GKE, AKS, or on-premises)
- Docker registry access (GitHub Container Registry, Docker Hub, private registry)

### Cluster Requirements

- **Minimum 2 nodes** (3+ for high availability)
- **3+ CPU cores** per node
- **4GB+ memory** per node
- **10Gi+ storage** (20Gi recommended)
- **Network policies** support (if using security policies)

### Kubernetes API Resources

Check cluster support:

```bash
# Verify API versions
kubectl api-resources | grep -E "deployment|statefulset|hpa|networkpolicy"

# Check storage classes
kubectl get storageclasses

# Verify Kubernetes version
kubectl version
```

---

## Quick Start (5 Minutes)

### 1. Create Secrets

```bash
# Create namespace
kubectl create namespace dataforge

# Create secrets from environment file
kubectl create secret generic dataforge-secrets \
  --from-env-file=.env.production \
  -n dataforge

# Or create individual secrets
kubectl create secret generic dataforge-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
  --from-literal=DATABASE_PASSWORD="$(openssl rand -base64 32)" \
  --from-literal=REDIS_PASSWORD="$(openssl rand -base64 32)" \
  --from-literal=VOYAGE_API_KEY="your-actual-key" \
  -n dataforge

# Verify secrets created
kubectl get secrets -n dataforge
```

### 2. Deploy Application

```bash
# Apply all manifests
kubectl apply -f k8s/dataforge.yaml

# Monitor deployment
kubectl rollout status deployment/dataforge-api -n dataforge
kubectl rollout status deployment/postgres -n dataforge
kubectl rollout status deployment/redis -n dataforge

# Check pod status
kubectl get pods -n dataforge

# Check services
kubectl get svc -n dataforge
```

### 3. Verify Deployment

```bash
# Check logs
kubectl logs -f deployment/dataforge-api -n dataforge

# Port forward to test
kubectl port-forward -n dataforge svc/dataforge-api 8000:80

# In another terminal
curl http://localhost:8000/health

# Check database connection
kubectl exec -it <postgres-pod> -n dataforge -- psql -U postgres -c "SELECT version();"
```

---

## Step-by-Step Deployment

### Phase 1: Infrastructure Setup

#### 1.1 Create Storage Classes (if needed)

```bash
# Check available storage classes
kubectl get storageclasses

# Create fast SSD storage class for database
cat << 'EOF' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: dataforge-fast
provisioner: ebs.csi.aws.com  # or your provisioner
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
EOF

# Update PVC to use fast storage
# Edit k8s/dataforge.yaml, set storageClassName: dataforge-fast
```

#### 1.2 Create Namespace with Labels

```bash
kubectl create namespace dataforge
kubectl label namespace dataforge name=dataforge
kubectl annotate namespace dataforge description="DataForge Production Environment"
```

#### 1.3 Setup RBAC (Role-Based Access Control)

```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dataforge
  namespace: dataforge

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dataforge
  namespace: dataforge
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dataforge
  namespace: dataforge
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: dataforge
subjects:
- kind: ServiceAccount
  name: dataforge
  namespace: dataforge
EOF
```

### Phase 2: Database & Cache Deployment

#### 2.1 Deploy PostgreSQL

```bash
# Extract just the Postgres deployment
kubectl apply -f - << 'EOF'
# (Copy the PostgreSQL Deployment, Service, and PVC from dataforge.yaml)
EOF

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n dataforge --timeout=300s

# Verify database
kubectl exec -it -n dataforge deployment/postgres -- psql -U postgres -c "\l"
```

#### 2.2 Run Database Migrations

```bash
# Port forward to local
kubectl port-forward -n dataforge svc/postgres 5432:5432 &

# Run Alembic migrations
DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@localhost:5432/dataforge" \
alembic upgrade head

# Kill port forward
pkill -f "port-forward"
```

#### 2.3 Deploy Redis

```bash
kubectl apply -f - << 'EOF'
# (Copy Redis Deployment, Service from dataforge.yaml)
EOF

# Verify Redis
kubectl exec -it -n dataforge deployment/redis -- redis-cli ping
```

### Phase 3: Application Deployment

#### 3.1 Create Image Pull Secrets (for private registries)

```bash
# For GitHub Container Registry
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=your-github-username \
  --docker-password=your-github-token \
  -n dataforge

# Add to ServiceAccount
kubectl patch serviceaccount dataforge -n dataforge -p \
  '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'
```

#### 3.2 Deploy API

```bash
# Deploy DataForge API
kubectl apply -f k8s/dataforge.yaml

# Monitor rollout
kubectl rollout status deployment/dataforge-api -n dataforge -w

# Check pod events
kubectl describe pod -l app=dataforge-api -n dataforge

# View logs
kubectl logs -f deployment/dataforge-api -n dataforge --all-containers

# Get deployment status
kubectl get deployment dataforge-api -n dataforge -o wide
```

#### 3.3 Verify API Health

```bash
# Port forward to test
kubectl port-forward -n dataforge svc/dataforge-api 8000:80 &

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger docs

# Check API metrics
curl http://localhost:8000/metrics | head -20

# Kill port forward
pkill -f "port-forward"
```

### Phase 4: Networking

#### 4.1 Setup Ingress (TLS/SSL)

```bash
# Install Ingress Controller (if not present)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.5.1/deploy/static/provider/aws/deploy.yaml

# Wait for controller
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Create TLS Secret
kubectl create secret tls dataforge-tls \
  --cert=path/to/server.crt \
  --key=path/to/server.key \
  -n dataforge

# Or use cert-manager for automatic certificates
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml
```

#### 4.2 Create Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dataforge
  namespace: dataforge
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
      secretName: dataforge-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dataforge-api
                port:
                  number: 80
```

Apply with:

```bash
kubectl apply -f ingress.yaml -n dataforge
```

### Phase 5: Monitoring

#### 5.1 Deploy Prometheus

```bash
# Create Prometheus deployment
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: dataforge
data:
  prometheus.yml: |
    # (Contents of prometheus.yml)

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: dataforge
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: dataforge
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        args:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--storage.tsdb.retention.time=30d'
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: storage
          mountPath: /prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: storage
        emptyDir: {}
EOF
```

#### 5.2 Deploy Grafana

```bash
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: dataforge
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus:9090
      isDefault: true

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: dataforge
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: dataforge-secrets
              key: GRAFANA_ADMIN_PASSWORD
        - name: GF_USERS_ALLOW_SIGN_UP
          value: "false"
        volumeMounts:
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
        - name: storage
          mountPath: /var/lib/grafana
      volumes:
      - name: datasources
        configMap:
          name: grafana-datasources
      - name: storage
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: dataforge
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
  type: LoadBalancer
EOF
```

---

## Production Operations

### Scaling

```bash
# Manual scaling
kubectl scale deployment dataforge-api --replicas=5 -n dataforge

# Check HPA status
kubectl get hpa -n dataforge

# View HPA metrics
kubectl describe hpa dataforge-api-hpa -n dataforge
```

### Updates & Rollouts

```bash
# Update image
kubectl set image deployment/dataforge-api \
  dataforge=ghcr.io/boswecw/dataforge:v1.2.3 \
  -n dataforge

# Monitor rollout
kubectl rollout status deployment/dataforge-api -n dataforge -w

# View rollout history
kubectl rollout history deployment/dataforge-api -n dataforge

# Rollback if needed
kubectl rollout undo deployment/dataforge-api -n dataforge
```

### Database Backups

```bash
# Backup PostgreSQL
kubectl exec -n dataforge deployment/postgres -- \
  pg_dump -U postgres dataforge > backup.sql

# Restore from backup
kubectl exec -i -n dataforge deployment/postgres -- \
  psql -U postgres < backup.sql
```

### Debugging

```bash
# Get pod details
kubectl describe pod <pod-name> -n dataforge

# View logs with timestamps
kubectl logs deployment/dataforge-api -n dataforge --timestamps=true

# Stream logs
kubectl logs -f deployment/dataforge-api -n dataforge

# Get events
kubectl get events -n dataforge --sort-by='.lastTimestamp'

# Execute commands in pod
kubectl exec -it <pod-name> -n dataforge -- /bin/bash

# Get resource usage
kubectl top nodes
kubectl top pods -n dataforge
```

### Monitoring

```bash
# Port forward to Grafana
kubectl port-forward -n dataforge svc/grafana 3000:3000 &
# Access: http://localhost:3000

# Port forward to Prometheus
kubectl port-forward -n dataforge svc/prometheus 9090:9090 &
# Access: http://localhost:9090
```

---

## Advanced Configuration

### High Availability (3+ Replicas)

```bash
# Edit dataforge-api replicas
kubectl patch deployment dataforge-api -n dataforge -p \
  '{"spec":{"replicas":3}}'

# Verify pod distribution across nodes
kubectl get pods -n dataforge -o wide
```

### Network Policies

```bash
# NetworkPolicy is already defined in dataforge.yaml
# Verify it's applied
kubectl get networkpolicy -n dataforge
kubectl describe networkpolicy dataforge-network-policy -n dataforge
```

### Resource Quotas

```bash
# Create namespace quota
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dataforge-quota
  namespace: dataforge
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    pods: "50"
EOF

# Check quota usage
kubectl describe quota -n dataforge
```

### Pod Disruption Budgets

```bash
# Ensure minimum replicas during maintenance
kubectl apply -f - << 'EOF'
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: dataforge-api-pdb
  namespace: dataforge
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: dataforge-api
EOF
```

---

## Troubleshooting

### Pod Won't Start

```bash
# Check events
kubectl describe pod <pod-name> -n dataforge

# Common issues:
# 1. Image pull error - check registry credentials
# 2. Out of resources - check node capacity
# 3. Volume mount errors - check PVC status
kubectl get pvc -n dataforge
kubectl get pv -n dataforge
```

### Database Connection Issues

```bash
# Test connectivity
kubectl run -it --rm debug --image=postgres:latest --restart=Never -n dataforge -- \
  psql -h postgres -U postgres -c "SELECT version();"

# Check PostgreSQL logs
kubectl logs deployment/postgres -n dataforge
```

### High Memory Usage

```bash
# Get memory usage by pod
kubectl top pods -n dataforge --sort-by=memory

# Check limits in deployment
kubectl get deployment dataforge-api -n dataforge -o yaml | grep -A 10 resources
```

---

## Cleanup

```bash
# Delete entire namespace (all resources)
kubectl delete namespace dataforge

# Or delete specific resources
kubectl delete deployment dataforge-api -n dataforge
kubectl delete pvc --all -n dataforge
```

---

## Support & Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [DataForge Repository](https://github.com/boswecw/dataforge)
- [Production Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
