# 部署指南

本文档介绍如何在不同环境中部署智能体API服务。

## 目录

- [本地开发部署](#本地开发部署)
- [Docker部署](#docker部署)
- [生产环境部署](#生产环境部署)
- [云平台部署](#云平台部署)
- [性能优化](#性能优化)

## 本地开发部署

### 前置要求

- Python 3.10+
- pip
- virtualenv（推荐）

### 部署步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd cus-ai-agent
```

2. **创建虚拟环境**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑.env文件，配置必要的环境变量
```

5. **启动服务**

```bash
# 方式一：使用启动脚本
chmod +x scripts/start.sh
./scripts/start.sh

# 方式二：直接运行
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

6. **验证部署**

访问 http://localhost:8000/docs 查看API文档

## Docker部署

### 前置要求

- Docker
- Docker Compose（可选）

### 使用Docker部署

1. **构建镜像**

```bash
docker build -t cus-ai-agent:latest .
```

2. **运行容器**

```bash
docker run -d \
  --name cus-ai-agent \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  cus-ai-agent:latest
```

3. **查看日志**

```bash
docker logs -f cus-ai-agent
```

4. **停止容器**

```bash
docker stop cus-ai-agent
docker rm cus-ai-agent
```

### 使用Docker Compose部署

1. **启动服务**

```bash
docker-compose up -d
```

2. **查看日志**

```bash
docker-compose logs -f
```

3. **停止服务**

```bash
docker-compose down
```

4. **重启服务**

```bash
docker-compose restart
```

### Docker镜像优化

创建`.dockerignore`文件：

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
.env
.git/
.gitignore
*.md
docs/
tests/
.pytest_cache/
logs/
```

## 生产环境部署

### 使用Gunicorn + Uvicorn

1. **安装Gunicorn**

```bash
pip install gunicorn
```

2. **创建Gunicorn配置文件**

创建`gunicorn.conf.py`：

```python
import multiprocessing

# 服务器配置
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 进程配置
daemon = False
pidfile = "logs/gunicorn.pid"

# 性能配置
keepalive = 5
timeout = 120
graceful_timeout = 30
```

3. **启动服务**

```bash
gunicorn src.api.main:app -c gunicorn.conf.py
```

### 使用Systemd管理服务

1. **创建服务文件**

创建`/etc/systemd/system/cus-ai-agent.service`：

```ini
[Unit]
Description=CUS AI Agent Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/cus-ai-agent
Environment="PATH=/opt/cus-ai-agent/venv/bin"
ExecStart=/opt/cus-ai-agent/venv/bin/gunicorn src.api.main:app -c gunicorn.conf.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **启动服务**

```bash
sudo systemctl daemon-reload
sudo systemctl start cus-ai-agent
sudo systemctl enable cus-ai-agent
```

3. **查看状态**

```bash
sudo systemctl status cus-ai-agent
```

### 使用Nginx反向代理

1. **安装Nginx**

```bash
sudo apt-get install nginx
```

2. **配置Nginx**

创建`/etc/nginx/sites-available/cus-ai-agent`：

```nginx
upstream agent_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://agent_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件缓存
    location /static/ {
        alias /opt/cus-ai-agent/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 日志
    access_log /var/log/nginx/agent_access.log;
    error_log /var/log/nginx/agent_error.log;
}
```

3. **启用配置**

```bash
sudo ln -s /etc/nginx/sites-available/cus-ai-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### HTTPS配置（使用Let's Encrypt）

```bash
# 安装Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 云平台部署

### AWS部署

#### 使用EC2

1. 启动EC2实例（Ubuntu 20.04）
2. 安装Docker
3. 部署应用

```bash
# 安装Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# 克隆项目
git clone <repository-url>
cd cus-ai-agent

# 配置环境变量
cp .env.example .env
vim .env

# 启动服务
docker-compose up -d
```

#### 使用ECS

1. 构建并推送Docker镜像到ECR
2. 创建ECS任务定义
3. 创建ECS服务
4. 配置负载均衡器

### 阿里云部署

#### 使用ECS

类似AWS EC2部署流程

#### 使用容器服务ACK

1. 创建Kubernetes集群
2. 部署应用

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cus-ai-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cus-ai-agent
  template:
    metadata:
      labels:
        app: cus-ai-agent
    spec:
      containers:
      - name: agent
        image: your-registry/cus-ai-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: cus-ai-agent-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: cus-ai-agent
```

## 性能优化

### 1. 应用层优化

- 使用多进程/多线程
- 启用连接池
- 实现缓存机制
- 异步处理

### 2. 数据库优化

- 使用连接池
- 添加索引
- 查询优化
- 读写分离

### 3. 缓存策略

使用Redis缓存：

```python
# 安装redis
pip install redis

# 配置缓存
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expire=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expire, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### 4. 负载均衡

使用Nginx进行负载均衡：

```nginx
upstream agent_backend {
    least_conn;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}
```

### 5. 监控和日志

- 使用Prometheus + Grafana监控
- 集中式日志管理（ELK Stack）
- 应用性能监控（APM）

## 安全建议

1. **环境变量管理**
   - 使用密钥管理服务（AWS Secrets Manager、阿里云KMS）
   - 不要在代码中硬编码密钥

2. **网络安全**
   - 配置防火墙规则
   - 使用HTTPS
   - 限制API访问频率

3. **应用安全**
   - 输入验证
   - SQL注入防护
   - XSS防护
   - CSRF防护

4. **访问控制**
   - 实现API密钥认证
   - 使用JWT令牌
   - 角色权限管理

## 故障排查

### 常见问题

1. **服务无法启动**
   - 检查端口是否被占用
   - 检查环境变量配置
   - 查看日志文件

2. **API响应慢**
   - 检查数据库连接
   - 检查网络延迟
   - 查看资源使用情况

3. **内存溢出**
   - 增加内存限制
   - 优化代码
   - 使用连接池

### 日志查看

```bash
# 查看应用日志
tail -f logs/app_*.log

# 查看Nginx日志
tail -f /var/log/nginx/agent_access.log
tail -f /var/log/nginx/agent_error.log

# 查看系统日志
journalctl -u cus-ai-agent -f
```

## 备份和恢复

### 数据备份

```bash
# 备份数据库
pg_dump -U user -d dbname > backup.sql

# 备份配置文件
tar -czf config_backup.tar.gz .env gunicorn.conf.py
```

### 恢复

```bash
# 恢复数据库
psql -U user -d dbname < backup.sql

# 恢复配置文件
tar -xzf config_backup.tar.gz
```

## 总结

本文档提供了智能体API服务的完整部署指南，包括：

- 本地开发环境部署
- Docker容器化部署
- 生产环境部署配置
- 云平台部署方案
- 性能优化建议
- 安全最佳实践
- 故障排查方法

根据实际需求选择合适的部署方案。

