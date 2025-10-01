# 智能体

## 需求
- 使用LangGraph编写智能体
- 暴露openapi，把 langgraph 流程包一层 HTTP 接口，走智能体编排（可能包含调用工具、数据库、外部 API、再调大模型）最终把结果返回给调用方。