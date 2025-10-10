"""
直接运行脚本
用于快速启动服务，无需shell脚本
"""
import os
import sys
import subprocess
from pathlib import Path

# 确保在项目根目录
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

# 尝试加载 .env 文件 (如果 python-dotenv 已安装)
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
        print("✅ .env 文件已加载")
except ImportError:
    print("⚠️  python-dotenv 未安装，将使用 Pydantic Settings 加载 .env")
    print("   建议安装: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  加载 .env 文件时出错: {e}")


def check_env_file():
    """检查.env文件是否存在"""
    if not os.path.exists(".env"):
        print("⚠️  警告: .env文件不存在")
        print("正在从.env.example创建.env文件...")
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ .env文件已创建")
            print("⚠️  请编辑.env文件，配置OPENAI_API_KEY等必要的环境变量")
            print("\n按Enter键继续，或Ctrl+C退出...")
            input()
        else:
            print("❌ 错误: .env.example文件不存在")
            sys.exit(1)


def create_logs_dir():
    """创建日志目录"""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("✅ 日志目录已创建")


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 启动智能体API服务")
    print("=" * 50)

    # 检查Python版本
    python_version = sys.version.split()[0]
    print(f"Python版本: {python_version}")

    # 检查.env文件
    check_env_file()

    # 创建日志目录
    create_logs_dir()

    # 从配置中读取端口和主机
    try:
        from src.config import settings
        api_host = settings.api_host
        api_port = settings.api_port
        print(f"\n配置加载成功:")
        print(f"  - 模型: {settings.model_name}")
        print(f"  - API地址: {api_host}:{api_port}")
        print(f"  - RAG工具: {'启用' if settings.enable_rag_tool else '禁用'}")
    except Exception as e:
        print(f"\n⚠️  配置加载失败，使用默认值: {e}")
        api_host = "0.0.0.0"
        api_port = 8000

    # 启动服务
    print("\n启动服务...")
    print(f"API文档: http://localhost:{api_port}/docs")
    print(f"健康检查: http://localhost:{api_port}/api/v1/health")
    print("\n按Ctrl+C停止服务")
    print("=" * 50)
    print()

    try:
        # 检查是否启用 reload 模式（默认不启用，避免多进程问题）
        enable_reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"

        # 构建启动命令
        cmd = [
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", api_host,
            "--port", str(api_port)
        ]

        if enable_reload:
            cmd.append("--reload")
            print("⚠️  开发模式: 启用自动重载")
        else:
            print("ℹ️  生产模式: 禁用自动重载")
            print("   如需启用自动重载，设置环境变量: UVICORN_RELOAD=true")

        # 使用uvicorn启动
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n请确保已安装所有依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

