"""
直接运行脚本
用于快速启动服务，无需shell脚本
"""
import os
import sys
import subprocess


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
    
    # 启动服务
    print("\n启动服务...")
    print("API文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/api/v1/health")
    print("\n按Ctrl+C停止服务")
    print("=" * 50)
    print()
    
    try:
        # 使用uvicorn启动
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n请确保已安装所有依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

