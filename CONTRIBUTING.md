# 贡献指南

感谢你对 cus-ai-agent 项目的关注！我们欢迎所有形式的贡献。

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [问题反馈](#问题反馈)

## 行为准则

参与本项目即表示你同意遵守我们的 [行为准则](CODE_OF_CONDUCT.md)。

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 检查 [Issues](https://github.com/wssaidong/cus-ai-agent/issues) 确认问题是否已被报告
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）
   - 相关日志或截图

### 提出新功能

如果你有新功能建议：

1. 先在 [Issues](https://github.com/wssaidong/cus-ai-agent/issues) 中讨论
2. 说明功能的用途和价值
3. 如果可能，提供实现思路

### 提交代码

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 开发流程

### 1. 环境准备

```bash
# 克隆你 fork 的仓库
git clone https://github.com/YOUR_USERNAME/cus-ai-agent.git
cd cus-ai-agent

# 添加上游仓库
git remote add upstream https://github.com/wssaidong/cus-ai-agent.git

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-cov black flake8 mypy
```

### 2. 创建分支

```bash
# 更新主分支
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature-name
```

### 3. 开发和测试

```bash
# 运行测试
pytest tests/

# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

### 4. 提交更改

```bash
# 添加更改
git add .

# 提交（遵循提交规范）
git commit -m "feat: add new feature"

# 推送到你的仓库
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

1. 访问你的 GitHub 仓库
2. 点击 "New Pull Request"
3. 填写 PR 描述，包括：
   - 更改内容
   - 相关 Issue
   - 测试情况
   - 截图（如适用）

## 代码规范

### Python 代码风格

我们遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范：

- 使用 4 个空格缩进
- 行长度不超过 100 字符
- 使用有意义的变量名
- 添加必要的注释和文档字符串

### 文档字符串

使用 Google 风格的文档字符串：

```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数简短描述
    
    详细描述（可选）
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
        
    Returns:
        返回值描述
        
    Raises:
        ValueError: 异常描述
    """
    pass
```

### 类型注解

尽可能使用类型注解：

```python
from typing import List, Dict, Optional

def process_data(data: List[Dict[str, str]]) -> Optional[str]:
    """处理数据"""
    pass
```

### 工具使用

优先使用 hutool 工具库（Java 项目）或标准库工具。

## 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 提交类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 示例

```bash
feat(agent): 添加新的工具调用功能

- 实现工具注册机制
- 添加工具调用日志
- 更新相关文档

Closes #123
```

## 测试要求

### 单元测试

- 新功能必须包含单元测试
- 测试覆盖率应保持在 80% 以上
- 使用 pytest 编写测试

```python
def test_calculator_tool():
    """测试计算器工具"""
    tool = CalculatorTool()
    result = tool._run("2 + 2")
    assert result == "4"
```

### 集成测试

对于涉及多个模块的功能，添加集成测试：

```python
def test_agent_with_tools():
    """测试智能体工具调用"""
    # 测试代码
    pass
```

## 文档要求

### 代码文档

- 所有公共函数和类必须有文档字符串
- 复杂逻辑需要添加注释
- 更新相关的 API 文档

### 用户文档

如果你的更改影响用户使用：

1. 更新 README.md
2. 在 `docs/` 目录添加或更新文档
3. 更新 CHANGELOG.md

## 问题反馈

### 获取帮助

- 查看 [文档](docs/)
- 搜索 [Issues](https://github.com/wssaidong/cus-ai-agent/issues)
- 在 Issue 中提问

### 联系方式

- GitHub Issues: 技术问题和 Bug 报告
- Pull Request: 代码贡献和讨论

## 许可证

通过贡献代码，你同意你的贡献将在 [MIT License](LICENSE) 下发布。

## 致谢

感谢所有为本项目做出贡献的开发者！

---

再次感谢你的贡献！🎉

