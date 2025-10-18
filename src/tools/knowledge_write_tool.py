"""
知识库写入工具 - 允许智能体将经验和知识写入到知识库
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime
from langchain.tools import BaseTool
from pydantic import Field, ConfigDict
from src.utils import app_logger
from src.tools.rag_tool import get_knowledge_base


class KnowledgeBaseWriteTool(BaseTool):
    """知识库写入工具 - 允许智能体将经验和知识写入到知识库"""

    name: str = "knowledge_base_write"
    description: str = """
    【智能体经验积累】将智能体的经验、解决方案、最佳实践等写入到知识库。

    【适用场景】：
    1. 记录解决问题的方案和步骤
    2. 保存最佳实践和经验总结
    3. 记录常见问题的解决方法
    4. 保存技术方案和架构设计
    5. 记录用户反馈和改进建议
    6. 保存项目经验和教训

    【输入格式】：
    输入应该是一个JSON字符串，包含以下字段：
    - content: 要写入的内容（必需）
    - title: 内容标题（可选）
    - category: 内容分类，如 solution, best_practice, faq, architecture, feedback（可选）
    - tags: 标签列表，用逗号分隔（可选）
    - source: 内容来源，如 agent_experience, user_feedback（可选）

    【示例输入】：
    {
        "content": "当遇到数据库连接超时时，可以通过增加连接池大小和调整超时时间来解决。",
        "title": "数据库连接超时解决方案",
        "category": "solution",
        "tags": "数据库,连接,超时",
        "source": "agent_experience"
    }

    【输出】：
    返回写入结果，包括文档ID和确认信息。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        """执行知识库写入"""
        try:
            # 解析输入
            params = json.loads(query)
            content = params.get("content")

            if not content:
                return "错误：缺少 content 字段，无法写入知识库"

            # 提取可选字段
            title = params.get("title", "")
            category = params.get("category", "agent_experience")
            tags = params.get("tags", "")
            source = params.get("source", "agent_experience")

            # 构建元数据 - 包含所有 Milvus 必需字段
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "type": "agent_experience",
                "file_name": title or "agent_experience",
                "file_type": "agent_experience",  # Milvus 必需字段
                "version": "1.0",  # Milvus 必需字段
                "author": "agent",  # Milvus 必需字段
                "uploaded_filename": title or "agent_experience"  # Milvus 必需字段
            }

            # 获取知识库实例
            kb = get_knowledge_base()

            # 添加到知识库
            ids = kb.add_texts([content], metadatas=[metadata])

            if ids:
                app_logger.info(f"成功将经验写入知识库: {title or '无标题'}")
                return f"""【知识库写入成功】

标题: {title or '无标题'}
分类: {category}
标签: {tags or '无'}
来源: {source}
文档ID: {ids[0]}
时间: {metadata['timestamp']}

内容已成功保存到知识库，可供后续查询和学习使用。
"""
            else:
                return "错误：写入知识库失败，未返回文档ID"

        except json.JSONDecodeError as e:
            app_logger.error(f"JSON解析失败: {str(e)}")
            return f"输入格式错误，请提供有效的JSON字符串: {str(e)}"
        except Exception as e:
            app_logger.error(f"知识库写入失败: {str(e)}")
            return f"知识库写入失败: {str(e)}"

    async def _arun(self, query: str) -> str:
        """异步执行知识库写入"""
        return self._run(query)


class KnowledgeBaseUpdateTool(BaseTool):
    """知识库更新工具 - 允许智能体更新已有的知识"""

    name: str = "knowledge_base_update"
    description: str = """
    【更新已有知识】更新知识库中已有的知识内容。

    【适用场景】：
    1. 更新过时的解决方案
    2. 改进已有的最佳实践
    3. 补充不完整的信息
    4. 修正错误的内容

    【输入格式】：
    输入应该是一个JSON字符串，包含以下字段：
    - content: 更新后的内容（必需）
    - title: 内容标题（可选）
    - category: 内容分类（可选）
    - tags: 标签列表（可选）
    - reason: 更新原因（可选）

    【示例输入】：
    {
        "content": "更新的内容...",
        "title": "更新的标题",
        "reason": "修正错误信息"
    }
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        """执行知识库更新"""
        try:
            # 解析输入
            params = json.loads(query)
            content = params.get("content")

            if not content:
                return "错误：缺少 content 字段，无法更新知识库"

            # 提取可选字段
            title = params.get("title", "")
            category = params.get("category", "agent_experience")
            tags = params.get("tags", "")
            reason = params.get("reason", "")

            # 构建元数据 - 包含所有 Milvus 必需字段
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "source": "agent_update",
                "timestamp": datetime.now().isoformat(),
                "type": "agent_experience",
                "update_reason": reason,
                "file_name": title or "agent_update",
                "file_type": "agent_update",  # Milvus 必需字段
                "version": "1.0",  # Milvus 必需字段
                "author": "agent",  # Milvus 必需字段
                "uploaded_filename": title or "agent_update"  # Milvus 必需字段
            }

            # 获取知识库实例
            kb = get_knowledge_base()

            # 添加更新的内容（作为新文档）
            ids = kb.add_texts([content], metadatas=[metadata])

            if ids:
                app_logger.info(f"成功更新知识库: {title or '无标题'}")
                return f"""【知识库更新成功】

标题: {title or '无标题'}
分类: {category}
更新原因: {reason or '无'}
文档ID: {ids[0]}
时间: {metadata['timestamp']}

内容已成功更新到知识库。
"""
            else:
                return "错误：更新知识库失败，未返回文档ID"

        except json.JSONDecodeError as e:
            app_logger.error(f"JSON解析失败: {str(e)}")
            return f"输入格式错误，请提供有效的JSON字符串: {str(e)}"
        except Exception as e:
            app_logger.error(f"知识库更新失败: {str(e)}")
            return f"知识库更新失败: {str(e)}"

    async def _arun(self, query: str) -> str:
        """异步执行知识库更新"""
        return self._run(query)

