# 系统架构图

本文档使用 Mermaid 图表展示系统的各个架构层次。

## 整体架构

```mermaid
graph TB
    subgraph "客户端层"
        A[Web 客户端]
        B[移动客户端]
        C[第三方应用]
    end
    
    subgraph "API 层"
        D[FastAPI 服务]
        E[路由处理]
        F[请求验证]
    end
    
    subgraph "智能体层"
        G[LangGraph 编排器]
        H[状态管理]
        I[节点执行器]
    end
    
    subgraph "工具层"
        J[计算器工具]
        K[文本处理工具]
        L[API 调用工具]
        M[数据库工具]
        N[RAG 检索工具]
    end
    
    subgraph "模型层"
        O[OpenAI API]
        P[通义千问 API]
        Q[其他 LLM]
    end
    
    subgraph "数据层"
        R[Milvus 向量库]
        S[关系数据库]
        T[文件存储]
    end
    
    subgraph "监控层"
        U[LangSmith 追踪]
        V[日志系统]
        W[性能监控]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    I --> J
    I --> K
    I --> L
    I --> M
    I --> N
    J --> O
    K --> O
    L --> O
    M --> S
    N --> R
    N --> O
    G --> U
    D --> V
    D --> W
```

## LangGraph 执行流程

```mermaid
graph LR
    A[开始] --> B[入口节点]
    B --> C[初始化状态]
    C --> D[LLM 节点]
    D --> E{需要工具?}
    E -->|是| F[工具调用]
    E -->|否| G[输出节点]
    F --> H[执行工具]
    H --> I{继续?}
    I -->|是| D
    I -->|否| G
    G --> J[格式化输出]
    J --> K[结束]
    
    style A fill:#90EE90
    style K fill:#FFB6C1
    style D fill:#87CEEB
    style F fill:#FFD700
```

## 请求处理流程

```mermaid
sequenceDiagram
    participant C as 客户端
    participant A as API 层
    participant G as LangGraph
    participant T as 工具层
    participant L as LLM
    participant D as 数据层
    
    C->>A: 发送请求
    A->>A: 验证请求
    A->>G: 创建智能体
    G->>G: 初始化状态
    
    loop 智能体执行
        G->>L: 调用 LLM
        L-->>G: 返回响应
        
        alt 需要工具
            G->>T: 调用工具
            T->>D: 查询数据
            D-->>T: 返回数据
            T-->>G: 工具结果
        end
    end
    
    G->>A: 返回最终结果
    A->>C: 响应客户端
```

## RAG 知识库架构

```mermaid
graph TB
    subgraph "文档处理"
        A[文档上传] --> B[文档加载器]
        B --> C[文本分割]
        C --> D[Embedding 生成]
    end
    
    subgraph "向量存储"
        D --> E[Milvus 向量库]
        E --> F[索引管理]
    end
    
    subgraph "检索流程"
        G[用户查询] --> H[查询 Embedding]
        H --> I[向量检索]
        I --> E
        E --> J[相似度计算]
        J --> K[结果排序]
    end
    
    subgraph "答案生成"
        K --> L[上下文构建]
        L --> M[LLM 生成]
        M --> N[答案返回]
    end
    
    style A fill:#90EE90
    style N fill:#FFB6C1
```

## 工具调用流程

```mermaid
graph LR
    A[智能体决策] --> B{选择工具}
    B -->|计算器| C[CalculatorTool]
    B -->|文本处理| D[TextProcessTool]
    B -->|API 调用| E[APICallTool]
    B -->|数据库| F[DatabaseTool]
    B -->|RAG 检索| G[RAGSearchTool]
    
    C --> H[执行计算]
    D --> I[处理文本]
    E --> J[调用外部 API]
    F --> K[查询数据库]
    G --> L[检索知识库]
    
    H --> M[返回结果]
    I --> M
    J --> M
    K --> M
    L --> M
    
    M --> N[继续执行]
    
    style A fill:#87CEEB
    style M fill:#FFD700
```

## 部署架构

```mermaid
graph TB
    subgraph "负载均衡层"
        A[Nginx/ALB]
    end
    
    subgraph "应用层"
        B[FastAPI 实例 1]
        C[FastAPI 实例 2]
        D[FastAPI 实例 N]
    end
    
    subgraph "服务层"
        E[Milvus 集群]
        F[PostgreSQL]
        G[Redis 缓存]
    end
    
    subgraph "外部服务"
        H[OpenAI API]
        I[LangSmith]
    end
    
    subgraph "监控层"
        J[Prometheus]
        K[Grafana]
        L[日志收集]
    end
    
    A --> B
    A --> C
    A --> D
    
    B --> E
    B --> F
    B --> G
    B --> H
    B --> I
    
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
    
    D --> E
    D --> F
    D --> G
    D --> H
    D --> I
    
    B --> J
    C --> J
    D --> J
    J --> K
    B --> L
    C --> L
    D --> L
```

## 数据流图

```mermaid
graph LR
    A[用户输入] --> B[API 接收]
    B --> C[请求验证]
    C --> D[智能体处理]
    D --> E{需要工具?}
    
    E -->|是| F[工具执行]
    F --> G[获取数据]
    G --> D
    
    E -->|否| H[LLM 推理]
    H --> I[生成响应]
    I --> J[格式化输出]
    J --> K[返回用户]
    
    D -.-> L[LangSmith 追踪]
    D -.-> M[日志记录]
    
    style A fill:#90EE90
    style K fill:#FFB6C1
```

## 模块依赖关系

```mermaid
graph TD
    A[main.py] --> B[routes.py]
    A --> C[knowledge_routes.py]
    B --> D[graph.py]
    B --> E[models.py]
    C --> F[rag_tool.py]
    D --> G[nodes.py]
    D --> H[state.py]
    G --> I[tools/__init__.py]
    I --> J[custom_tools.py]
    I --> K[database.py]
    I --> L[api_caller.py]
    I --> F
    F --> M[document_loader.py]
    A --> N[settings.py]
    A --> O[logger.py]
    
    style A fill:#FFD700
    style D fill:#87CEEB
    style I fill:#90EE90
```

## 配置管理

```mermaid
graph TB
    A[.env 文件] --> B[settings.py]
    B --> C[API 配置]
    B --> D[模型配置]
    B --> E[工具配置]
    B --> F[日志配置]
    B --> G[RAG 配置]
    
    C --> H[FastAPI 应用]
    D --> I[LLM 初始化]
    E --> J[工具加载]
    F --> K[日志系统]
    G --> L[向量库连接]
    
    style A fill:#90EE90
    style B fill:#FFD700
```

---

## 说明

以上图表展示了系统的主要架构和流程。你可以：

1. 在支持 Mermaid 的编辑器中查看（如 VS Code + Mermaid 插件）
2. 在 GitHub 上直接查看（GitHub 原生支持 Mermaid）
3. 使用在线工具如 [Mermaid Live Editor](https://mermaid.live/) 查看和编辑

## 相关文档

- [架构设计文档](architecture.md)
- [快速开始](quickstart.md)
- [部署指南](deployment.md)

