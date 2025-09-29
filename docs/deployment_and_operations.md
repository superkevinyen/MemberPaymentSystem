# MPS 部署與運維指南

## 📋 目錄
- [1. 環境準備](#1-環境準備)
- [2. 部署流程](#2-部署流程)
- [3. 配置管理](#3-配置管理)
- [4. 監控運維](#4-監控運維)
- [5. 故障排除](#5-故障排除)
- [6. 維護操作](#6-維護操作)
- [7. 性能調優](#7-性能調優)
- [8. 安全運維](#8-安全運維)

---

## 1. 環境準備

### 1.1 基礎設施需求

#### 🖥️ 硬件配置建議

| 環境 | CPU | 內存 | 存儲 | 網絡 | 節點數量 |
|------|-----|------|------|------|----------|
| **開發環境** | 2 vCPU | 4GB | 50GB SSD | 100Mbps | 1 |
| **測試環境** | 4 vCPU | 8GB | 100GB SSD | 1Gbps | 2 |
| **生產環境** | 8 vCPU | 16GB | 500GB SSD | 10Gbps | 3+ |
| **災備環境** | 8 vCPU | 16GB | 500GB SSD | 10Gbps | 3+ |

#### 🌐 網絡架構
```mermaid
graph TB
    subgraph "外部網絡"
        INTERNET[Internet]
        CDN[CDN]
    end
    
    subgraph "DMZ 區域"
        LB[負載均衡器]
        WAF[Web 應用防火牆]
    end
    
    subgraph "應用區域"
        APP1[應用服務器1]
        APP2[應用服務器2]
        APP3[應用服務器3]
    end
    
    subgraph "數據區域"
        DB_MASTER[主數據庫]
        DB_SLAVE1[從數據庫1]
        DB_SLAVE2[從數據庫2]
        REDIS[Redis 集群]
    end
    
    subgraph "管理區域"
        MONITOR[監控服務]
        LOG[日誌服務]
        BACKUP[備份服務]
    end
    
    INTERNET --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> DB_MASTER
    APP2 --> DB_SLAVE1
    APP3 --> DB_SLAVE2
    APP1 --> REDIS
    APP2 --> REDIS
    APP3 --> REDIS
    
    DB_MASTER --> DB_SLAVE1
    DB_MASTER --> DB_SLAVE2
    
    APP1 --> MONITOR
    APP2 --> MONITOR
    APP3 --> MONITOR
    
    MONITOR --> LOG
    MONITOR --> BACKUP
```

### 1.2 軟件環境

#### 📦 依賴軟件清單
```yaml
# 基礎軟件
operating_system: "Ubuntu 22.04 LTS"
container_runtime: "Docker 24.0+"
orchestration: "Kubernetes 1.28+"
reverse_proxy: "Nginx 1.24+"

# 數據庫
database: "PostgreSQL 15+"
cache: "Redis 7.0+"
search: "Elasticsearch 8.0+"

# 監控
monitoring: "Prometheus + Grafana"
logging: "ELK Stack"
tracing: "Jaeger"

# 安全
ssl_certificate: "Let's Encrypt / 商業證書"
secrets_management: "HashiCorp Vault"
backup: "Restic + S3"
```

#### 🔧 環境變量配置
```bash
# .env.production
# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 數據庫配置
DATABASE_URL=postgresql://user:password@host:5432/mps_production
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT=30

# Redis 配置
REDIS_URL=redis://redis-cluster:6379
REDIS_POOL_SIZE=10

# 安全配置
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key
API_RATE_LIMIT=1000

# 監控配置
PROMETHEUS_ENDPOINT=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
LOG_LEVEL=info

# 外部服務
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
ALIPAY_APP_ID=your-alipay-app-id
```

---

## 2. 部署流程

### 2.1 Supabase 部署

#### 🚀 Supabase 項目初始化
```bash
# 1. 創建 Supabase 項目
npx supabase init

# 2. 啟動本地開發環境
npx supabase start

# 3. 應用數據庫遷移
npx supabase db reset

# 4. 部署到生產環境
npx supabase db push --linked
```

#### 📊 數據庫初始化腳本
```sql
-- init_production.sql
-- 1. 創建擴展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. 執行 schema 文件
\i schema/mps_schema.sql

-- 3. 執行 RPC 文件
\i rpc/mps_rpc.sql

-- 4. 創建初始數據
INSERT INTO app.membership_levels(level, name, min_points, max_points, discount, is_active) VALUES
  (0, '普通會員', 0, 999, 1.000, true),
  (1, '銀卡會員', 1000, 4999, 0.950, true),
  (2, '金卡會員', 5000, 9999, 0.900, true),
  (3, '鑽石會員', 10000, null, 0.850, true)
ON CONFLICT (level) DO NOTHING;

-- 5. 創建系統用戶
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'admin@mps.system',
  crypt('admin_password', gen_salt('bf')),
  now(),
  now(),
  now()
) ON CONFLICT (email) DO NOTHING;
```

### 2.2 容器化部署

#### 🐳 Docker 配置
```dockerfile
# Dockerfile.production
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runtime

# 安全配置
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

WORKDIR /app

# 複製構建產物
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# 設置權限
USER nextjs

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

EXPOSE 3000

CMD ["npm", "start"]
```

#### 🚢 Docker Compose 配置
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
    depends_on:
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    networks:
      - mps-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    restart: unless-stopped
    networks:
      - mps-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - nginx_logs:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - mps-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - mps-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - mps-network

volumes:
  redis_data:
  nginx_logs:
  prometheus_data:
  grafana_data:

networks:
  mps-network:
    driver: bridge
```

### 2.3 Kubernetes 部署

#### ⚙️ K8s 部署配置
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mps-production

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mps-config
  namespace: mps-production
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  API_RATE_LIMIT: "1000"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mps-secrets
  namespace: mps-production
type: Opaque
data:
  supabase-url: <base64-encoded-url>
  supabase-service-key: <base64-encoded-key>
  jwt-secret: <base64-encoded-secret>
  redis-password: <base64-encoded-password>

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mps-app
  namespace: mps-production
  labels:
    app: mps
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mps
  template:
    metadata:
      labels:
        app: mps
        version: v1.0.0
    spec:
      containers:
      - name: mps-app
        image: mps:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          valueFrom:
            configMapKeyRef:
              name: mps-config
              key: NODE_ENV
        - name: SUPABASE_URL
          valueFrom:
            secretKeyRef:
              name: mps-secrets
              key: supabase-url
        - name: SUPABASE_SERVICE_ROLE_KEY
          valueFrom:
            secretKeyRef:
              name: mps-secrets
              key: supabase-service-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: app-logs
          mountPath: /app/logs
      volumes:
      - name: app-logs
        emptyDir: {}

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mps-service
  namespace: mps-production
spec:
  selector:
    app: mps
  ports:
    - protocol: TCP
      port: 80
      targetPort: 3000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mps-ingress
  namespace: mps-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.mps.example.com
    secretName: mps-tls
  rules:
  - host: api.mps.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mps-service
            port:
              number: 80

---
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mps-hpa
  namespace: mps-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mps-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2.4 CI/CD 流水線

#### 🔄 GitHub Actions 工作流
```yaml
# .github/workflows/deploy.yml
name: Deploy MPS to Production

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: mps_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run linting
      run: npm run lint
    
    - name: Run type checking
      run: npm run type-check
    
    - name: Run unit tests
      run: npm run test:unit
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/mps_test
        REDIS_URL: redis://localhost:6379
    
    - name: Run integration tests
      run: npm run test:integration
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/mps_test
        REDIS_URL: redis://localhost:6379
    
    - name: Run security audit
      run: npm audit --audit-level high

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./Dockerfile.production
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to Staging
      run: |
        echo "Deploying to staging environment..."
        # 部署到測試環境的腳本
        ./scripts/deploy-staging.sh
      env:
        KUBECONFIG: ${{ secrets.STAGING_KUBECONFIG }}
        IMAGE_TAG: ${{ github.sha }}

  deploy-production:
    needs: [build, deploy-staging]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to Production
      run: |
        echo "Deploying to production environment..."
        # 部署到生產環境的腳本
        ./scripts/deploy-production.sh
      env:
        KUBECONFIG: ${{ secrets.PRODUCTION_KUBECONFIG }}
        IMAGE_TAG: ${{ github.ref_name }}
    
    - name: Run smoke tests
      run: |
        echo "Running smoke tests..."
        ./scripts/smoke-tests.sh
      env:
        API_ENDPOINT: https://api.mps.example.com
        API_KEY: ${{ secrets.PRODUCTION_API_KEY }}
    
    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 3. 配置管理

### 3.1 環境配置

#### 🔧 配置文件結構
```
config/
├── environments/
│   ├── development.yml
│   ├── staging.yml
│   └── production.yml
├── secrets/
│   ├── development.env
│   ├── staging.env
│   └── production.env
└── nginx/
    ├── nginx.conf
    ├── ssl/
    └── sites-available/
```

#### 📝 生產環境配置
```yaml
# config/environments/production.yml
app:
  name: "MPS Production"
  version: "1.0.0"
  port: 3000
  log_level: "info"
  
database:
  pool_size: 20
  timeout: 30000
  ssl: true
  
redis:
  pool_size: 10
  timeout: 5000
  
security:
  rate_limit:
    window_ms: 60000
    max_requests: 1000
  cors:
    origin: ["https://app.mps.example.com"]
    credentials: true
  
monitoring:
  prometheus:
    enabled: true
    port: 9090
  health_check:
    enabled: true
    interval: 30
  
features:
  qr_rotation:
    enabled: true
    default_ttl: 900
  payment_retry:
    enabled: true
    max_attempts: 3
  audit_logging:
    enabled: true
    retention_days: 2555  # 7年
```

#### 🔐 密鑰管理
```bash
#!/bin/bash
# scripts/manage-secrets.sh

# 使用 HashiCorp Vault 管理密鑰
vault_write() {
    local path=$1
    local key=$2
    local value=$3
    
    vault kv put secret/mps/$path $key="$value"
}

vault_read() {
    local path=$1
    local key=$2
    
    vault kv get -field=$key secret/mps/$path
}

# 初始化生產環境密鑰
init_production_secrets() {
    vault_write "production/database" "url" "$DATABASE_URL"
    vault_write "production/supabase" "service_key" "$SUPABASE_SERVICE_ROLE_KEY"
    vault_write "production/jwt" "secret" "$JWT_SECRET"
    vault_write "production/encryption" "key" "$ENCRYPTION_KEY"
    vault_write "production/redis" "password" "$REDIS_PASSWORD"
}

# 輪換密鑰
rotate_secrets() {
    local environment=$1
    
    # 生成新的 JWT 密鑰
    new_jwt_secret=$(openssl rand -base64 32)
    vault_write "$environment/jwt" "secret" "$new_jwt_secret"
    
    # 生成新的加密密鑰
    new_encryption_key=$(openssl rand -base64 32)
    vault_write "$environment/encryption" "key" "$new_encryption_key"
    
    echo "Secrets rotated for environment: $environment"
}
```

### 3.2 Nginx 配置

#### 🌐 反向代理配置
```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # 日誌格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/access.log main;
    
    # 基本設置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;
    
    # Gzip 壓縮
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/javascript application/xml+rss 
               application/json application/xml;
    
    # 安全頭
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 上游服務器
    upstream mps_backend {
        least_conn;
        server app1:3000 max_fails=3 fail_timeout=30s;
        server app2:3000 max_fails=3 fail_timeout=30s;
        server app3:3000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=payment:10m rate=5r/s;
    
    # 主服務器配置
    server {
        listen 80;
        server_name api.mps.example.com;
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name api.mps.example.com;
        
        # SSL 配置
        ssl_certificate /etc/nginx/ssl/mps.crt;
        ssl_certificate_key /etc/nginx/ssl/mps.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # API 路由
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://mps_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # 超時設置
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # 支付 API 特殊限流
        location /api/payment/ {
            limit_req zone=payment burst=10 nodelay;
            
            proxy_pass http://mps_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # 健康檢查
        location /health {
            access_log off;
            proxy_pass http://mps_backend;
        }
        
        # 靜態文件
        location /static/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            alias /var/www/static/;
        }
    }
}
```

---

## 4. 監控運維

### 4.1 監控體系

#### 📊 Prometheus 配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # MPS 應用監控
  - job_name: 'mps-app'
    static_configs:
      - targets: ['app1:3000', 'app2:3000', 'app3:3000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  # PostgreSQL 監控
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  # Redis 監控
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    
  # Nginx 監控
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
    
  # 節點監控
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

#### 🚨 告警規則
```yaml
# rules/mps-alerts.yml
groups:
- name: mps.rules
  rules:
  # 應用可用性告警
  - alert: MPSAppDown
    expr: up{job="mps-app"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "MPS application is down"
      description: "MPS application {{ $labels.instance }} has been down for more than 1 minute."
  
  # 高錯誤率告警
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second."
  
  # 響應時間告警
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time"
      description: "95th percentile response time is {{ $value }} seconds."
  
  # 數據庫連接告警
  - alert: DatabaseConnectionHigh
    expr: pg_stat_activity_count > 80
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High database connections"
      description: "Database has {{ $value }} active connections."
  
  # 支付失敗率告警
  - alert: PaymentFailureRate
    expr: rate(payment_transactions_total{status="failed"}[5m]) / rate(payment_transactions_total[5m]) > 0.05
    for: 3m
    labels:
      severity: critical
    annotations:
      summary: "High payment failure rate"
      description: "Payment failure rate is {{ $value | humanizePercentage }}."
  
  # QR 碼過期率告警
  - alert: QRExpirationRate
    expr: rate(qr_codes_total{status="expired"}[5m]) / rate(qr_codes_total[5m]) > 0.3
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High QR code expiration rate"
      description: "QR code expiration rate is {{ $value | humanizePercentage }}."
```

#### 📈 Grafana 儀表板
```json
{
  "dashboard": {
    "title": "MPS System Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Payment Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(payment_transactions_total{status=\"completed\"}[5m]) / rate(payment_transactions_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_activity_count",
            "legendFormat": "Active Connections"
          },
          {
            "expr": "rate(pg_stat_database_tup_inserted[5m])",
            "legendFormat": "Inserts/sec"
          }
        ]
      }
    ]
  }
}
```

### 4.2 日誌管理

#### 📝 結構化日誌配置
```javascript
// logger.js
const winston = require('winston');
const { ElasticsearchTransport } = require('winston-elasticsearch');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'mps-api',
    version: process.env.APP_VERSION,
    environment: process.env.NODE_ENV
  },
  transports: [
    // 控制台輸出
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    
    // 文件輸出
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 10485760, // 10MB
      maxFiles: 5
    }),
    
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 10485760, // 10MB
      maxFiles: 10
    }),
    
    // Elasticsearch 輸出
    new ElasticsearchTransport({
      level: 'info',
      clientOpts: {
        node: process.env.ELASTICSEARCH_URL
      },
      index: 'mps-logs'
    })
  ]
});

// 業務日誌記錄器
const businessLogger = {
  payment: (action, data) => {
    logger.info('Payment operation', {
      category: 'payment',
      action,
      ...data
    });
  },
  
  qr: (action, data) => {
    logger.info('QR operation', {
      category: 'qr',
      action,
      ...data
    });
  },
  
  security: (action, data) => {
    logger.warn('Security event', {
      category: 'security',
      action,
      ...data
    });
  }
};

module.exports = { logger, businessLogger };
```

#### 🔍 日誌分析腳本
```python
# scripts/log-analysis.py
import json
import pandas as pd
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta

class LogAnalyzer:
    def __init__(self, es_host):
        self.es = Elasticsearch([es_host])
    
    def analyze_payment_patterns(self, days=7):
        """分析支付模式"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"category": "payment"}},
                        {"range": {"@timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat()
                        }}}
                    ]
                }
            },
            "aggs": {
                "hourly_volume": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "interval": "hour"
                    }
                },
                "merchant_distribution": {
                    "terms": {"field": "merchant_id"}
                },
                "error_analysis": {
                    "terms": {"field": "error_code"}
                }
            }
        }
        
        result = self.es.search(index="mps-logs", body=query)
        return self.process_payment_analysis(result)
    
    def detect_anomalies(self):
        """檢測異常模式"""
        # 檢測異常高頻的失敗
        failed_payments_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"category": "payment"}},
                        {"term": {"action": "failed"}},
                        {"range": {"@timestamp": {"gte": "now-1h"}}}
                    ]
                }
            },
            "aggs": {
                "error_codes": {
                    "terms": {"field": "error_code"}
                }
            }
        }
        
        # 檢測異常大額交易
        large_payments_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"category": "payment"}},
                        {"term": {"action": "completed"}},
                        {"range": {"amount": {"gte": 50000}}},
                        {"range": {"@timestamp": {"gte": "now-1h"}}}
                    ]
                }
            }
        }
        
        failed_result = self.es.search(index="mps-logs", body=failed_payments_query)
        large_result = self.es.search(index="mps-logs", body=large_payments_query)
        
        return {
            "failed_payments": failed_result,
            "large_payments": large_result
        }
    
    def generate_daily_report(self):
        """生成日報"""
        yesterday = datetime.now() - timedelta(days=1)
        
        report = {
            "date": yesterday.strftime("%Y-%m-%d"),
            "payment_stats": self.get_payment_stats(yesterday),
            "error_summary": self.get_error_summary(yesterday),
            "performance_metrics": self.get_performance_metrics(yesterday)
        }
        
        return report
```

---

## 5. 故障排除

### 5.1 常見問題診斷

#### 🔧 診斷腳本
```bash
#!/bin/bash
# scripts/diagnose.sh

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查系統狀態
check_system_health() {
    log_info "Checking system health..."
    
    # 檢查應用服務
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        log_info "Application is healthy"
    else
        log_error "Application health check failed"
        return 1
    fi
    
    # 檢查數據庫連接
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        log_info "Database is accessible"
    else
        log_error "Database connection failed"
        return 1
    fi
    
    # 檢查 Redis 連接
    if redis-cli ping > /dev/null 2>&1; then
        log_info "Redis is accessible"
    else
        log_error "Redis connection failed"
        return 1
    fi
    
    return 0
}

# 檢查支付功能
check_payment_functionality() {
    log_info "Checking payment functionality..."
    
    # 測試 QR 碼生成
    local qr_response=$(curl -s -X POST http://localhost:3000/api/qr/rotate \
        -H "Content-Type: application/json" \
        -d '{"card_id":"test-card-id","ttl_seconds":300}')
    
    if echo "$qr_response" | jq -e '.qr_plain' > /dev/null 2>&1; then
        log_info "QR code generation is working"
    else
        log_error "QR code generation failed"
        echo "Response: $qr_response"
        return 1
    fi
    
    return 0
}

# 檢查數據庫性能
check_database_performance() {
    log_info "Checking database performance..."
    
    # 檢查活躍連接數
    local active_connections=$(psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)
    
    if [ "$active_connections" -gt 50 ]; then
        log_warn "High number of active connections: $active_connections"
    else
        log_info "Active connections: $active_connections"
    fi
    
    # 檢查慢查詢
    local slow_queries=$(psql -t -c "SELECT count(*) FROM pg_stat_statements WHERE mean_time > 1000;" 2>/dev/null | xargs)
    
    if [ "$slow_queries" -gt 0 ]; then
        log_warn "Found $slow_queries slow queries"
        psql -c "SELECT query, calls, mean_time FROM pg_stat_statements WHERE mean_time > 1000 ORDER BY mean_time DESC LIMIT 5;"
    else
        log_info "No slow queries detected"
    fi
}

# 檢查磁盤空間
check_disk_space() {
    log_info "Checking disk space..."
    
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt 80 ]; then
        log_error "Disk usage is high: ${disk_usage}%"
        return 1
    elif [ "$disk_usage" -gt 70 ]; then
        log_warn "Disk usage is moderate: ${disk_usage}%"
    else
        log_info "Disk usage is normal: ${disk_usage}%"
    fi
    
    return 0
}

# 檢查內存使用
check_memory_usage() {
    log_info "Checking memory usage..."
    
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$memory_usage" -gt 90 ]; then
        log_error "Memory usage is critical: ${memory_usage}%"
        return 1
    elif [ "$memory_usage" -gt 80 ]; then
        log_warn "Memory usage is high: ${memory_usage}%"
    else
        log_info "Memory usage is normal: ${memory_usage}%"
    fi
    
    return 0
}

# 主診斷函數
main() {
    log_info "Starting MPS system diagnosis..."
    
    local exit_code=0
    
    check_system_health || exit_code=1
    check_payment_functionality || exit_code=1
    check_database_performance || exit_code=1
    check_disk_space || exit_code=1
    check_memory_usage || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        log_info "All checks passed successfully"
    else
        log_error "Some checks failed. Please review the output above."
    fi
    
    exit $exit_code
}

# 執行診斷
main "$@"
```

### 5.2 故障恢復流程

#### 🔄 自動恢復腳本
```python
# scripts/auto-recovery.py
import subprocess
import time
import logging
import requests
from typing import Dict, List

class AutoRecovery:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recovery_actions = {
            'app_down': self.restart_application,
            'db_connection_failed': self.restart_database_connection,
            'high_memory': self.restart_application,
            'disk_full': self.cleanup_logs,
            'payment_failures': self.restart_payment_service
        }
    
    def detect_issues(self) -> List[str]:
        """檢測系統問題"""
        issues = []
        
        # 檢查應用健康狀態
        try:
            response = requests.get('http://localhost:3000/health', timeout=5)
            if response.status_code != 200:
                issues.append('app_down')
        except requests.RequestException:
            issues.append('app_down')
        
        # 檢查數據庫連接
        try:
            result = subprocess.run(['pg_isready', '-h', 'localhost'], 
                                  capture_output=True, timeout=5)
            if result.returncode != 0:
                issues.append('db_connection_failed')
        except subprocess.TimeoutExpired:
            issues.append('db_connection_failed')
        
        # 檢查內存使用
        try:
            result = subprocess.run(['free'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            memory_line = lines[1].split()
            used = int(memory_line[2])
            total = int(memory_line[1])
            if (used / total) > 0.9:
                issues.append('high_memory')
        except Exception as e:
            self.logger.error(f"Memory check failed: {e}")
        
        # 檢查磁盤空間
        try:
            result = subprocess.run(['df', '/'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            disk_line = lines[1].split()
            usage_percent = int(disk_line[4].rstrip('%'))
            if usage_percent > 95:
                issues.append('disk_full')
        except Exception as e:
            self.logger.error(f"Disk check failed: {e}")
        
        return issues
    
    def restart_application(self):
        """重啟應用服務"""
        self.logger.info("Restarting application...")
        try:
            # 使用 systemd 重啟服務
            subprocess.run(['systemctl', 'restart', 'mps-app'], check=True)
            time.sleep(30)  # 等待服務啟動
            
            # 驗證服務是否正常
            response = requests.get('http://localhost:3000/health', timeout=10)
            if response.status_code == 200:
                self.logger.info("Application restarted successfully")
                return True
            else:
                self.logger.error("Application restart failed - health check failed")
                return False
        except Exception as e:
            self.logger.error(f"Application restart failed: {e}")
            return False
    
    def restart_database_connection(self):
        """重啟數據庫連接"""
        self.logger.info("Restarting database connection...")
        try:
            # 重啟連接池
            subprocess.run(['systemctl', 'restart', 'pgbouncer'], check=True)
            time.sleep(10)
            
            # 驗證連接
            result = subprocess.run(['pg_isready', '-h', 'localhost'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                self.logger.info("Database connection restored")
                return True
            else:
                self.logger.error("Database connection restart failed")
                return False
        except Exception as e:
            self.logger.error(f"Database connection restart failed: {e}")
            return False
    
    def cleanup_logs(self):
        """清理日誌文件"""
        self.logger.info("Cleaning up log files...")
        try:
            # 清理舊日誌
            subprocess.run(['find', '/var/log', '-name', '*.log', 
                          '-mtime', '+7', '-delete'], check=True)
            
            # 清理應用日誌
            subprocess.run(['find', '/app/logs', '-name', '*.log', 
                          '-mtime', '+3', '-delete'], check=True)
            
            # 壓縮大日誌文件
            subprocess.run(['find', '/var/log', '-name', '*.log', 
                          '-size', '+100M', '-exec', 'gzip', '{}', ';'], 
                         check=True)
            
            self.logger.info("Log cleanup completed")
            return True
        except Exception as e:
            self.logger.error(f"Log cleanup failed: {e}")
            return False
    
    def restart_payment_service(self):
        """重啟支付服務"""
        self.logger.info("Restarting payment service...")
        try:
            # 清理 Redis 緩存
            subprocess.run(['redis-cli', 'FLUSHDB'], check=True)
            
            # 重啟應用
            return self.restart_application()
        except Exception as e:
            self.logger.error(f"Payment service restart failed: {e}")
            return False
    
    def run_recovery(self):
        """執行自動恢復"""
        issues = self.detect_issues()
        
        if not issues:
            self.logger.info("No issues detected")
            return True
        
        self.logger.warning(f"Detected issues: {issues}")
        
        recovery_success = True
        for issue in issues:
            if issue in self.recovery_actions:
                self.logger.info(f"Attempting to recover from: {issue}")
                success = self.recovery_actions[issue]()
                if not success:
                    recovery_success = False
                    self.logger.error(f"Failed to recover from: {issue}")
            else:
                self.logger.warning(f"No recovery action defined for: {issue}")
                recovery_success = False
        
        return recovery_success

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    recovery = AutoRecovery()
    
    while True:
        try:
            recovery.run_recovery()
            time.sleep(60)  # 每分鐘檢查一次
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Recovery process error: {e}")
            time.sleep(60)
```

---

## 6. 維護操作

### 6.1 定期維護任務

#### 🔄 維護腳本
```bash
#!/bin/bash
# scripts/maintenance.sh

# 設置維護模式
enable_maintenance_mode() {
    echo "Enabling maintenance mode..."
    
    # 創建維護頁面
    cat > /var/www/maintenance.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>系統維護中</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>系統維護中</h1>
    <p>系統正在進行維護，預計 30 分鐘後恢復服務。</p>
    <p>如有緊急情況，請聯繫客服。</p>
</body>
</html>
EOF
    
    # 更新 Nginx 配置
    cp /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/default
    nginx -s reload
    
    echo "Maintenance mode enabled"
}

# 禁用維護模式
disable_maintenance_mode() {
    echo "Disabling maintenance mode..."
    
    # 恢復正常配置
    cp /etc/nginx/sites-available/production /etc/nginx/sites-enabled/default
    nginx -s reload
    
    echo "Maintenance mode disabled"
}

# 數據庫維護
database_maintenance() {
    echo "Starting database maintenance..."
    
    # 更新統計信息
    psql -c "ANALYZE;"
    
    # 清理過期數據
    psql -c "DELETE FROM app.card_qr_history WHERE issued_at < NOW() - INTERVAL '90 days';"
    
    # 重建索引
    psql -c "REINDEX DATABASE mps_production;"
    
    # 清理 WAL 文件
    psql -c "SELECT pg_switch_wal();"
    
    echo "Database maintenance completed"
}

# 應用維護
application_maintenance() {
    echo "Starting application maintenance..."
    
    # 清理臨時文件
    find /tmp -name "mps-*" -mtime +1 -delete
    
    # 清理應用緩存
    redis-cli FLUSHDB
    
    # 重啟應用服務
    systemctl restart mps-app
    
    # 等待服務啟動
    sleep 30
    
    # 驗證服務狀態
    if curl -f http://localhost:3000/health; then
        echo "Application maintenance completed successfully"
    else
        echo "Application maintenance failed - service not healthy"
        exit 1
    fi
}

# 日誌維護
log_maintenance() {
    echo "Starting log maintenance..."
    
    # 歸檔舊日誌
    find /var/log/mps -name "*.log" -mtime +7 -exec gzip {} \;
    
    # 刪除過期日誌
    find /var/log/mps -name "*.gz" -mtime +30 -delete
    
    # 清理 Docker 日誌
    docker system prune -f
    
    echo "Log maintenance completed"
}

# 備份維護
backup_maintenance() {
    echo "Starting backup maintenance..."
    
    # 創建數據庫備份
    pg_dump mps_production | gzip > /backup/mps_$(date +%Y%m%d_%H%M%S).sql.gz
    
    # 上傳到雲存儲
    aws s3 cp /backup/mps_$(date +%Y%m%d_%H%M%S).sql.gz s3://mps-backups/
    
    # 清理本地舊備份
    find /backup -name "mps_*.sql.gz" -mtime +7 -delete
    
    echo "Backup maintenance completed"
}

# 安全維護
security_maintenance() {
    echo "Starting security maintenance..."
    
    # 更新系統包
    apt update && apt upgrade -y
    
    # 檢查安全漏洞
    npm audit --audit-level high
    
    # 輪換密鑰
    ./rotate-secrets.sh production
    
    # 檢查異常登入
    grep "Failed password" /var/log/auth.log | tail -20
    
    echo "Security maintenance completed"
}

# 主維護函數
main() {
    local maintenance_type=${1:-"full"}
    
    case $maintenance_type in
        "database")
            database_maintenance
            ;;
        "application")
            application_maintenance
            ;;
        "logs")
            log_maintenance
            ;;
        "backup")
            backup_maintenance
            ;;
        "security")
            security_maintenance
            ;;
        "full")
            enable_maintenance_mode
            database_maintenance
            application_maintenance
            log_maintenance
            backup_maintenance
            security_maintenance
            disable_maintenance_mode
            ;;
        *)
            echo "Usage: $0 {database|application|logs|backup|security|full}"
            exit 1
            ;;
    esac
    
    echo "Maintenance completed: $maintenance_type"
}

# 執行維護
main "$@"
```

### 6.2 數據庫維護

#### 🗄️ 數據庫優化腳本
```sql
-- database_optimization.sql

-- 1. 更新表統計信息
ANALYZE app.transactions;
ANALYZE app.member_cards;
ANALYZE app.merchants;
ANALYZE app.card_qr_state;
ANALYZE audit.event_log;

-- 2. 重建碎片化索引
REINDEX INDEX CONCURRENTLY idx_transactions_composite;
REINDEX INDEX CONCURRENTLY idx_tx_card_time;
REINDEX INDEX CONCURRENTLY idx_tx_merchant_time;

-- 3. 清理過期數據
DELETE FROM app.card_qr_history 
WHERE issued_at < NOW() - INTERVAL '90 days';

DELETE FROM audit.event_log 
WHERE happened_at < NOW() - INTERVAL '2 years'
  AND action NOT IN ('PAYMENT', 'REFUND', 'RECHARGE');

-- 4. 優化表空間
VACUUM (ANALYZE, VERBOSE) app.transactions;
VACUUM (ANALYZE, VERBOSE) app.member_cards;
VACUUM (ANALYZE, VERBOSE) audit.event_log;

-- 5. 檢查表膨脹
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE schemaname IN ('app', 'audit')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 6. 檢查未使用的索引
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE idx_scan = 0
ORDER BY schemaname, tablename;

-- 7. 檢查慢查詢
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 7. 性能調優

### 7.1 數據庫調優

#### ⚡ PostgreSQL 配置優化
```ini
# postgresql.conf 生產環境配置

# 連接設置
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 512MB

# WAL 設置
wal_buffers = 64MB
checkpoint_completion_target = 0.9
wal_writer_delay = 200ms
commit_delay = 100

# 查詢優化
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 1000

# 日誌設置
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# 自動清理
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 30s
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
```

### 7.2 應用層調優

#### 🚀 Node.js 性能優化
```javascript
// performance-config.js
const cluster = require('cluster');
const os = require('os');

// 集群配置
if (cluster.isMaster) {
    const numCPUs = os.cpus().length;
    
    // 創建工作進程
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }
    
    cluster.on('exit', (worker, code, signal) => {
        console.log(`Worker ${worker.process.pid} died`);
        cluster.fork();
    });
} else {
    // 工作進程配置
    const app = require('./app');
    
    // 性能優化設置
    process.env.UV_THREADPOOL_SIZE = 128;
    
    // 內存監控
    setInterval(() => {
        const memUsage = process.memoryUsage();
        if (memUsage.heapUsed > 1024 * 1024 * 1024) { // 1GB
            console.warn('High memory usage detected:', memUsage);
        }
    }, 60000);
    
    // 優雅關閉
    process.on('SIGTERM', () => {
        console.log('SIGTERM received, shutting down gracefully');
        server.close(() => {
            process.exit(0);
        });
    });
    
    const server = app.listen(process.env.PORT || 3000);
}

// 連接池優化
const poolConfig = {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    
    // 連接池設置
    min: 5,
    max: 20,
    acquireTimeoutMillis: 30000,
    createTimeoutMillis: 30000,
    destroyTimeoutMillis: 5000,
    idleTimeoutMillis: 300000,
    reapIntervalMillis: 1000,
    createRetryIntervalMillis: 200,
    
    // 性能優化
    propagateCreateError: false
};
```

---

## 8. 安全運維

### 8.1 安全檢查清單

#### 🔒 日常安全檢查
```bash
#!/bin/bash
# scripts/security-check.sh

# 安全檢查清單
security_checklist() {
    echo "=== MPS Security Checklist ==="
    
    # 1. 檢查系統更新
    echo "1. Checking system updates..."
    apt list --upgradable 2>/dev/null | grep -v "WARNING" | wc -l
    
    # 2. 檢查開放端口
    echo "2. Checking open ports..."
    netstat -tuln | grep LISTEN
    
    # 3. 檢查失敗登入
    echo "3. Checking failed login attempts..."
    grep "Failed password" /var/log/auth.log | tail -10
    
    # 4. 檢查 SSL 證書
    echo "4. Checking SSL certificate..."
    openssl x509 -in /etc/nginx/ssl/mps.crt -text -noout | grep "Not After"
    
    # 5. 檢查文件權限
    echo "5. Checking file permissions..."
    find /app -type f -perm /o+w -ls
    
    # 6. 檢查進程
    echo "6. Checking running processes..."
    ps aux | grep -E "(nginx|node|postgres|redis)" | grep -v grep
    
    # 7. 檢查磁盤加密
    echo "7. Checking disk encryption..."
    lsblk -f | grep crypto
    
    # 8. 檢查防火牆狀態
    echo "8. Checking firewall status..."
    ufw status
    
    # 9. 檢查入侵檢測
    echo "9. Checking intrusion detection..."
    if command -v fail2ban-client &> /dev/null; then
        fail2ban-client status
    fi
    
    # 10. 檢查備份狀態
    echo "10. Checking backup status..."
    ls -la /backup/ | tail -5
}

# 漏洞掃描
vulnerability_scan() {
    echo "=== Vulnerability Scan ==="
    
    # NPM 安全審計
    echo "Running npm audit..."
    npm audit --audit-level high
    
    # Docker 鏡像掃描
    echo "Scanning Docker images..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image mps:latest
    
    # 系統漏洞掃描
    echo "Scanning system vulnerabilities..."
    if command -v lynis &> /dev/null; then
        lynis audit system --quick
    fi
}

# 安全配置檢查
security_config_check() {
    echo "=== Security Configuration Check ==="
    
    # 檢查 SSH 配置
    echo "Checking SSH configuration..."
    grep -E "PermitRootLogin|PasswordAuthentication|Port" /etc/ssh/sshd_config
    
    # 檢查 Nginx 安全頭
    echo "Checking Nginx security headers..."
    curl -I https://api.mps.example.com | grep -E "X-Frame-Options|X-Content-Type-Options|Strict-Transport-Security"
    
    # 檢查數據庫配置
    echo "Checking database security..."
    psql -c "SHOW ssl;" 2>/dev/null
    psql -c "SELECT name, setting FROM pg_settings WHERE name LIKE '%log%';" 2>/dev/null
}

# 執行所有檢查
main() {
    security_checklist
    echo ""
    vulnerability_scan
    echo ""
    security_config_check
}

main "$@"
```

### 8.2 事件響應

#### 🚨 安全事件響應流程
```python
# scripts/incident-response.py
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class IncidentResponse:
    def __init__(self):
        self.severity_levels = {
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 3,
            'CRITICAL': 4
        }
        
        self.response_teams = {
            'security': ['security@company.com'],
            'devops': ['devops@company.com'],
            'management': ['cto@company.com']
        }
    
    def detect_security_incident(self, log_entry: dict) -> dict:
        """檢測安全事件"""
        incident = None
        
        # 檢測暴力破解攻擊
        if self.is_brute_force_attack(log_entry):
            incident = {
                'type': 'brute_force_attack',
                'severity': 'HIGH',
                'description': 'Multiple failed login attempts detected',
                'source_ip': log_entry.get('ip_address'),
                'timestamp': datetime.now().isoformat()
            }
        
        # 檢測異常大額交易
        elif self.is_suspicious_transaction(log_entry):
            incident = {
                'type': 'suspicious_transaction',
                'severity': 'MEDIUM',
                'description': 'Unusually large transaction detected',
                'transaction_id': log_entry.get('transaction_id'),
                'amount': log_entry.get('amount'),
                'timestamp': datetime.now().isoformat()
            }
        
        # 檢測 SQL 注入嘗試
        elif self.is_sql_injection_attempt(log_entry):
            incident = {
                'type': 'sql_injection',
                'severity': 'CRITICAL',
                'description': 'SQL injection attempt detected',
                'source_ip': log_entry.get('ip_address'),
                'query': log_entry.get('query'),
                'timestamp': datetime.now().isoformat()
            }
        
        return incident
    
    def respond_to_incident(self, incident: dict):
        """響應安全事件"""
        severity = incident['severity']
        incident_type = incident['type']
        
        # 記錄事件
        self.log_incident(incident)
        
        # 根據嚴重程度採取行動
        if severity == 'CRITICAL':
            self.critical_response(incident)
        elif severity == 'HIGH':
            self.high_response(incident)
        elif severity == 'MEDIUM':
            self.medium_response(incident)
        else:
            self.low_response(incident)
    
    def critical_response(self, incident: dict):
        """關鍵事件響應"""
        # 立即通知所有團隊
        self.notify_teams(['security', 'devops', 'management'], incident)
        
        # 自動阻斷
        if incident['type'] == 'sql_injection':
            self.block_ip(incident.get('source_ip'))
        
        # 啟動事件響應流程
        self.initiate_incident_response(incident)
    
    def high_response(self, incident: dict):
        """高級事件響應"""
        # 通知安全和運維團隊
        self.notify_teams(['security', 'devops'], incident)
        
        # 增強監控
        self.enhance_monitoring(incident)
        
        if incident['type'] == 'brute_force_attack':
            self.block_ip(incident.get('source_ip'))
    
    def medium_response(self, incident: dict):
        """中級事件響應"""
        # 通知安全團隊
        self.notify_teams(['security'], incident)
        
        # 記錄詳細信息
        self.collect_evidence(incident)
    
    def low_response(self, incident: dict):
        """低級事件響應"""
        # 僅記錄，定期審查
        self.log_for_review(incident)
    
    def block_ip(self, ip_address: str):
        """阻斷 IP 地址"""
        if ip_address:
            # 添加到防火牆黑名單
            subprocess.run(['ufw', 'deny', 'from', ip_address])
            
            # 添加到 fail2ban
            subprocess.run(['fail2ban-client', 'set', 'sshd', 'banip', ip_address])
    
    def notify_teams(self, teams: list, incident: dict):
        """通知響應團隊"""
        for team in teams:
            if team in self.response_teams:
                self.send_alert_email(self.response_teams[team], incident)
                self.send_slack_notification(incident)
    
    def send_alert_email(self, recipients: list, incident: dict):
        """發送告警郵件"""
        msg = MIMEMultipart()
        msg['From'] = 'security@company.com'
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Security Incident Alert - {incident['type']}"
        
        body = f"""
        Security Incident Detected
        
        Type: {incident['type']}
        Severity: {incident['severity']}
        Description: {incident['description']}
        Timestamp: {incident['timestamp']}
        
        Please investigate immediately.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # 發送郵件
        server = smtplib.SMTP('localhost')
        server.send_message(msg)
        server.quit()
    
    def send_slack_notification(self, incident: dict):
        """發送 Slack 通知"""
        webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
        
        payload = {
            "text": f"🚨 Security Incident: {incident['type']}",
            "attachments": [
                {
                    "color": "danger" if incident['severity'] == 'CRITICAL' else "warning",
                    "fields": [
                        {"title": "Severity", "value": incident['severity'], "short": True},
                        {"title": "Type", "value": incident['type'], "short": True},
                        {"title": "Description", "value": incident['description'], "short": False}
                    ]
                }
            ]
        }
        
        requests.post(webhook_url, json=payload)
```

這個部署與運維指南為 MPS 系統提供了完整的生產環境部署、監控、維護和安全運維方案，確保系統能夠穩定、安全地運行在生產環境中。

<update_todo_list>
<todos>
[x] 深入分析現有系統架構和業務邏輯
[x] 創建完整的系統架構圖 (Mermaid)
[x] 梳理詳細的業務需求和用例
[x] 更新 README.md 包含完整的系統概述
[x] 更新 docs/Architecture.md 包含詳細的技術架構
[x] 創建數據流程圖和業務流程圖
[x] 補充安全性和擴展性分析
[x] 添加部署和運維指南
</todos>
</update_todo_list>