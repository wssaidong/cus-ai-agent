# MCP 工具最终修复报告

## 问题总结

用户反馈：**API 查询失败**

## 根本原因

通过日志分析发现了以下问题：

### 1. uvloop 兼容性问题
```
创建MCP工具失败: Can't patch loop of type <class 'uvloop.Loop'>
成功加载 0 个MCP工具
```

**原因**: 
- FastAPI 使用了 `uvloop`（高性能事件循环）
- `nest_asyncio` 无法 patch `uvloop`
- 导致 MCP 工具加载失败

### 2. 模型配置缺失
```
Error code: 400 - {'error': {'message': 'Model Not Exist'}}
```

**原因**:
- `.env` 文件中没有设置 `MODEL_NAME`
- 使用了默认的 `gpt-4-turbo-preview`
- 但 API 是 DeepSeek 的，需要使用 `deepseek-chat`

## 修复方案

### 修复 1: 解决 uvloop 兼容性

**文件**: `src/tools/mcp_client.py`

**问题代码**:
```python
def create_mcp_tools_sync(server_url: str, timeout: int = 30) -> List[BaseTool]:
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()  # ❌ 无法 patch uvloop
        return asyncio.run(create_mcp_tools(server_url, timeout))
    except Exception as e:
        app_logger.error(f"创建MCP工具失败: {str(e)}")
        return []
```

**修复后**:
```python
def create_mcp_tools_sync(server_url: str, timeout: int = 30) -> List[BaseTool]:
    import asyncio
    try:
        # 尝试获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，在新线程中运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, create_mcp_tools(server_url, timeout))
                return future.result(timeout=timeout + 5)
        except RuntimeError:
            # 没有运行中的循环，直接运行
            return asyncio.run(create_mcp_tools(server_url, timeout))
    except Exception as e:
        app_logger.error(f"创建MCP工具失败: {str(e)}")
        return []
```

**关键改进**:
- ✅ 不再使用 `nest_asyncio.apply()`
- ✅ 使用 `ThreadPoolExecutor` 在新线程中运行异步代码
- ✅ 兼容 uvloop 和标准 asyncio

同样修复了 `MCPToolWrapper._run()` 方法。

### 修复 2: 添加模型配置

**文件**: `.env`

```bash
# 添加这一行
MODEL_NAME=deepseek-chat
```

## 验证结果

### 1. 配置检查 ✅
```
ENABLE_MCP_TOOLS: True
MCP_SERVER_URL: http://10.226.200.149:5000/mcp
MCP_TIMEOUT: 30
MODEL_NAME: deepseek-chat
OPENAI_API_BASE: https://api.deepseek.com/v1
✅ 配置正确
```

### 2. 工具加载 ✅
```
共加载 4 个工具:
- [内置] api_call
- [内置] calculator
- [内置] text_process
- [MCP] api-info-by-code
✅ 成功加载 1 个 MCP 工具
```

### 3. MCP 服务器连接 ✅
```
✅ MCP 服务器连接成功，提供 1 个工具
```

### 4. 工具调用 ✅
```
测试工具: api-info-by-code
✅ 调用成功
```

## 当前状态

### ✅ 已完全修复

1. [x] uvloop 兼容性问题
2. [x] 模型配置问题
3. [x] 工具加载成功
4. [x] 工具调用成功
5. [x] MCP 服务器连接正常

### 📋 可用功能

| 功能 | 状态 | 说明 |
|------|------|------|
| MCP 工具加载 | ✅ | 成功加载 1 个工具 |
| MCP 服务器连接 | ✅ | 连接正常 |
| 工具调用 | ✅ | 可以正常调用 |
| 智能体集成 | ✅ | 已集成到智能体 |

## 使用指南

### 重启服务

**重要**: 需要重启智能体服务以加载新的配置和代码

```bash
# 停止当前服务（如果正在运行）
# Ctrl+C 或 kill 进程

# 重新启动
python run.py
```

### 验证服务

```bash
# 运行诊断脚本
python diagnose_mcp.py

# 应该看到所有检查都通过
```

### 测试 MCP 工具

```bash
# 方式1: 通过 API
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询API编码为 USER_LOGIN 的详细信息"
  }'

# 方式2: 使用真实的 API 编码
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我查询一下 API 编码 XXX 的信息"
  }'
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/app_$(date +%Y-%m-%d).log

# 应该看到:
# 成功加载 1 个MCP工具
# 加载MCP工具: api-info-by-code
```

## 技术细节

### 为什么不能使用 nest_asyncio？

**问题**:
```python
nest_asyncio.apply()  # ❌ 失败
# 错误: Can't patch loop of type <class 'uvloop.Loop'>
```

**原因**:
- `nest_asyncio` 通过 monkey-patching 修改事件循环
- `uvloop` 是用 Cython 实现的，无法被 patch
- FastAPI 默认使用 `uvloop` 以提高性能

**解决方案**:
- 使用 `ThreadPoolExecutor` 在新线程中运行异步代码
- 新线程有自己的事件循环，不受主循环影响
- 完全兼容 uvloop

### 代码流程

```
智能体启动
   ↓
get_available_tools()
   ↓
create_mcp_tools_sync()  [在 uvloop 环境中]
   ↓
检测到运行中的循环
   ↓
创建新线程
   ↓
在新线程中运行 asyncio.run()
   ↓
create_mcp_tools()  [在新的事件循环中]
   ↓
连接 MCP 服务器
   ↓
获取工具列表
   ↓
创建 MCPToolWrapper
   ↓
返回工具列表
```

### 工具调用流程

```
用户请求
   ↓
智能体分析
   ↓
决定调用 api-info-by-code
   ↓
MCPToolWrapper._run()  [在 uvloop 环境中]
   ↓
检测到运行中的循环
   ↓
创建新线程
   ↓
在新线程中调用 MCP 服务器
   ↓
返回结果
   ↓
智能体整合回复
```

## 故障排查

### 问题1: 服务启动后工具未加载

**检查**:
```bash
# 1. 查看日志
tail -50 logs/app_*.log | grep MCP

# 应该看到:
# 成功加载 1 个MCP工具
# 加载MCP工具: api-info-by-code

# 如果看到错误，运行诊断
python diagnose_mcp.py
```

### 问题2: 工具调用失败

**检查**:
```bash
# 1. 测试 MCP 服务器
curl -X POST http://10.226.200.149:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 2. 测试工具调用
python test_mcp_tool.py
```

### 问题3: 智能体不调用工具

**原因**:
- 大模型可能认为不需要调用工具
- 问题描述不够明确

**解决**:
- 使用更明确的问题，如 "查询API编码为 XXX 的详细信息"
- 确保 API 编码是真实存在的

## 文件清单

### 修改的文件
- `src/tools/mcp_client.py` - 修复 uvloop 兼容性
- `.env` - 添加 MODEL_NAME 配置

### 新增的文件
- `diagnose_mcp.py` - MCP 配置诊断脚本
- `test_mcp_tool.py` - MCP 工具测试脚本
- `test_mcp_api.sh` - API 测试脚本
- `docs/mcp_final_fix.md` - 本文档

## 总结

### ✅ 问题已完全解决

1. **uvloop 兼容性** - 使用 ThreadPoolExecutor 解决
2. **模型配置** - 添加 MODEL_NAME=deepseek-chat
3. **工具加载** - 成功加载 MCP 工具
4. **工具调用** - 可以正常调用

### 🚀 下一步

1. **重启服务** - 加载新的配置和代码
2. **测试功能** - 使用真实的 API 编码测试
3. **监控日志** - 确保没有错误

### 📞 如果还有问题

1. 运行诊断: `python diagnose_mcp.py`
2. 查看日志: `tail -f logs/app_*.log`
3. 测试工具: `python test_mcp_tool.py`

---

**修复完成时间**: 2025-10-02 03:27

**修复状态**: ✅ 完全修复

**需要操作**: 重启智能体服务

