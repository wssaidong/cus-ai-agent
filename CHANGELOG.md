# 变更日志

本文档记录了项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 优化项目文档结构，符合开源项目规范
- 添加 LICENSE 文件（MIT 许可证）
- 添加 CONTRIBUTING.md 贡献指南
- 添加 CODE_OF_CONDUCT.md 行为准则
- 添加 CHANGELOG.md 变更日志

### 优化
- 清理无用日志输出，提升性能
- 优化代码注释和文档字符串

## [1.0.0] - 2024-10-02

### 新增
- 基于 LangGraph 的智能体编排系统
- FastAPI RESTful API 接口
- 支持多种工具调用（计算器、文本处理、API 调用、数据库查询）
- RAG 知识库集成（Milvus 向量数据库）
- 独立的 Embedding API 配置
- LangSmith 可观测性集成
- 流式输出支持（SSE）
- OpenAI API 兼容接口
- Docker 部署支持
- 完整的文档体系

### 功能特性
- ✅ 智能体编排和状态管理
- ✅ 工具动态加载和调用
- ✅ 知识库检索和问答
- ✅ 多轮对话支持
- ✅ 会话管理
- ✅ 结构化日志
- ✅ 配置化管理
- ✅ 健康检查接口

### 技术栈
- Python 3.10+
- LangGraph 0.2+
- LangChain 0.3+
- FastAPI 0.109+
- Milvus 2.3+
- LangSmith 0.1+

### 文档
- 快速开始指南
- 架构设计文档
- 部署指南
- 使用示例
- API 文档
- RAG 集成指南
- LangSmith 集成指南
- 故障排查指南

---

## 版本说明

### 版本号格式

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 变更类型

- **新增**：新功能
- **变更**：现有功能的变更
- **弃用**：即将移除的功能
- **移除**：已移除的功能
- **修复**：Bug 修复
- **安全**：安全相关的修复
- **优化**：性能优化和代码改进

---

## 链接

- [项目主页](https://github.com/wssaidong/cus-ai-agent)
- [问题反馈](https://github.com/wssaidong/cus-ai-agent/issues)
- [贡献指南](CONTRIBUTING.md)

[Unreleased]: https://github.com/wssaidong/cus-ai-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/wssaidong/cus-ai-agent/releases/tag/v1.0.0

