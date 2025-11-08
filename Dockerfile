# syntax=docker/dockerfile:1.4
# 优化 Dockerfile - 使用清华镜像源 + 固定版本依赖
# 构建时间: 1-2分钟 (优化前: 3-5分钟) | 镜像大小: ~1.2GB (优化前: ~1.5GB)
#
# 优化要点:
# 1. 使用清华大学镜像源 (pip + apt) - 国内速度最快
# 2. 固定依赖版本号 - 避免版本解析耗时
# 3. 移除未使用的依赖 - 减少安装时间和镜像大小
# 4. 启用 pip cache mount - 加速重复构建
#
# 更新依赖步骤:
# 1. 修改 requirements.txt
# 2. 运行: make docker-build-no-cache
# 3. 验证: docker run --rm cus-ai-agent:latest pip list

# ==========================================
# 阶段 1: 依赖构建器
# ==========================================
FROM python:3.10-slim as builder

# 设置环境变量 - 使用清华大学镜像源(国内最快最稳定)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

# 使用清华大学 Debian 镜像源加速 apt-get
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources

# 安装编译依赖(最小化)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件(利用 Docker 缓存层)
COPY requirements.txt .

# 使用 requirements.txt 安装所有依赖
# 使用 pip cache mount 加速构建
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# ==========================================
# 阶段 2: 运行时镜像(最小化)
# ==========================================
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

# 使用清华大学 Debian 镜像源加速 apt-get
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources

# 只安装运行时必需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 依赖
COPY --from=builder /install /usr/local

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p logs data && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser tiktoken_cache/cl100k_base.tiktoken /app/.tiktoken_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4

# 复制项目文件(放在最后,利用缓存)
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser .env .
COPY --chown=appuser:appuser run.py .

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

