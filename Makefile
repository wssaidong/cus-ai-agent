.PHONY: help install dev-install test lint format clean run docker-build docker-run docs

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)cus-ai-agent Makefile 命令:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## 安装依赖
	@echo "$(BLUE)安装依赖...$(NC)"
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "$(GREEN)✓ 依赖安装完成$(NC)"

dev-install: install ## 安装开发依赖
	@echo "$(BLUE)安装开发依赖...$(NC)"
	pip install pytest pytest-cov black flake8 mypy pre-commit
	pre-commit install
	@echo "$(GREEN)✓ 开发依赖安装完成$(NC)"

test: ## 运行测试
	@echo "$(BLUE)运行测试...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)✓ 测试完成$(NC)"

test-cov: ## 运行测试并生成覆盖率报告
	@echo "$(BLUE)运行测试并生成覆盖率报告...$(NC)"
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ 覆盖率报告已生成: htmlcov/index.html$(NC)"

lint: ## 代码检查
	@echo "$(BLUE)运行代码检查...$(NC)"
	flake8 src/ tests/ --max-line-length=100
	@echo "$(GREEN)✓ 代码检查完成$(NC)"

format: ## 格式化代码
	@echo "$(BLUE)格式化代码...$(NC)"
	black src/ tests/
	@echo "$(GREEN)✓ 代码格式化完成$(NC)"

type-check: ## 类型检查
	@echo "$(BLUE)运行类型检查...$(NC)"
	mypy src/
	@echo "$(GREEN)✓ 类型检查完成$(NC)"

clean: ## 清理临时文件
	@echo "$(BLUE)清理临时文件...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "$(GREEN)✓ 清理完成$(NC)"

run: ## 启动服务
	@echo "$(BLUE)启动服务...$(NC)"
	python run.py

dev: ## 开发模式启动（自动重载）
	@echo "$(BLUE)开发模式启动...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build: ## 构建 Docker 镜像
	@echo "$(BLUE)构建 Docker 镜像...$(NC)"
	@bash scripts/build_docker.sh
	@echo "$(GREEN)✓ Docker 镜像构建完成$(NC)"

docker-build-no-cache: ## 强制重新构建 Docker 镜像(不使用缓存)
	@echo "$(BLUE)强制重新构建 Docker 镜像...$(NC)"
	@bash scripts/build_docker.sh --no-cache
	@echo "$(GREEN)✓ Docker 镜像构建完成$(NC)"

docker-run: ## 运行 Docker 容器
	@echo "$(BLUE)运行 Docker 容器...$(NC)"
	docker run -p 8000:8000 --env-file .env cus-ai-agent:latest

docker-compose-up: ## 使用 Docker Compose 启动
	@echo "$(BLUE)使用 Docker Compose 启动...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ 服务已启动$(NC)"

docker-compose-down: ## 停止 Docker Compose 服务
	@echo "$(BLUE)停止 Docker Compose 服务...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ 服务已停止$(NC)"

milvus-start: ## 启动 Milvus
	@echo "$(BLUE)启动 Milvus...$(NC)"
	./scripts/start_milvus.sh
	@echo "$(GREEN)✓ Milvus 已启动$(NC)"

logs: ## 查看日志
	@echo "$(BLUE)查看日志...$(NC)"
	tail -f logs/app_$$(date +%Y-%m-%d).log

check: lint type-check test ## 运行所有检查（lint + type-check + test）
	@echo "$(GREEN)✓ 所有检查通过$(NC)"

setup: install ## 初始化项目
	@echo "$(BLUE)初始化项目...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)请编辑 .env 文件配置环境变量$(NC)"
	@echo "$(GREEN)✓ 项目初始化完成$(NC)"

docs-serve: ## 启动文档服务器（需要安装 mkdocs）
	@echo "$(BLUE)启动文档服务器...$(NC)"
	@if command -v mkdocs >/dev/null 2>&1; then \
		mkdocs serve; \
	else \
		echo "$(RED)错误: 未安装 mkdocs$(NC)"; \
		echo "运行: pip install mkdocs mkdocs-material"; \
	fi

api-test: ## 测试 API
	@echo "$(BLUE)测试 API...$(NC)"
	./scripts/test_api.sh

health-check: ## 健康检查
	@echo "$(BLUE)健康检查...$(NC)"
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool || echo "$(RED)服务未运行$(NC)"

version: ## 显示版本信息
	@echo "$(BLUE)版本信息:$(NC)"
	@python --version
	@pip --version
	@echo "项目版本: $$(grep 'API_VERSION' .env.example | cut -d'=' -f2)"

update-deps: ## 更新依赖
	@echo "$(BLUE)更新依赖...$(NC)"
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ 依赖更新完成$(NC)"

freeze: ## 冻结依赖版本
	@echo "$(BLUE)冻结依赖版本...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✓ 依赖版本已冻结$(NC)"

pre-commit: format lint type-check ## 提交前检查
	@echo "$(GREEN)✓ 提交前检查完成$(NC)"

ci: clean install check ## CI 流程
	@echo "$(GREEN)✓ CI 流程完成$(NC)"

all: clean install check run ## 完整流程（清理、安装、检查、运行）
	@echo "$(GREEN)✓ 完整流程完成$(NC)"

