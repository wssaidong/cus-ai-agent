"""
RAG (Retrieval-Augmented Generation) 知识库工具 - Milvus 版本
"""
import os
import json
import uuid
from typing import Optional, List, Dict, Any
from langchain.tools import BaseTool
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document
from pydantic import Field, ConfigDict
from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType
from src.utils import app_logger
from src.config import settings


class RAGKnowledgeBase:
    """RAG 知识库管理类 - Milvus 版本"""

    def __init__(
        self,
        milvus_host: str,
        milvus_port: int,
        collection_name: str,
        embedding_model: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        milvus_user: Optional[str] = None,
        milvus_password: Optional[str] = None
    ):
        """
        初始化 RAG 知识库

        Args:
            milvus_host: Milvus 服务器地址
            milvus_port: Milvus 服务器端口
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
            milvus_user: Milvus 用户名
            milvus_password: Milvus 密码
        """
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.milvus_user = milvus_user
        self.milvus_password = milvus_password
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 初始化嵌入模型
        # 优先使用 RAG 专用的 API 配置，如果没有则回退到全局配置
        embedding_api_key = settings.rag_openai_api_key or settings.openai_api_key
        embedding_api_base = settings.rag_openai_api_base or settings.openai_api_base

        if not embedding_api_key:
            raise ValueError(
                "未配置 Embedding API Key。请设置 RAG_OPENAI_API_KEY 或 OPENAI_API_KEY"
            )

        app_logger.info(f"初始化 RAG Embedding 配置:")
        app_logger.info(f"  - API Base: {embedding_api_base}")
        app_logger.info(f"  - 模型: {embedding_model}")
        app_logger.info(f"  - 使用独立配置: {'是' if settings.rag_openai_api_key else '否（使用全局配置）'}")

        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=embedding_api_key,
            openai_api_base=embedding_api_base
        )

        # 连接到 Milvus
        try:
            connect_args = {
                "alias": "default",
                "host": milvus_host,
                "port": milvus_port
            }
            # 如果提供了用户名和密码,则添加到连接参数中
            if milvus_user and milvus_password:
                connect_args["user"] = milvus_user
                connect_args["password"] = milvus_password
                app_logger.info(f"使用认证连接到 Milvus: {milvus_host}:{milvus_port} (用户: {milvus_user})")
            else:
                app_logger.info(f"连接到 Milvus: {milvus_host}:{milvus_port} (无认证)")

            connections.connect(**connect_args)
            app_logger.info(f"成功连接到 Milvus: {milvus_host}:{milvus_port}")
        except Exception as e:
            app_logger.error(f"连接 Milvus 失败: {str(e)}")
            raise

        # 初始化向量数据库
        # 使用 uri 参数而不是 connection_args，确保 langchain_milvus 正确连接
        milvus_uri = f"http://{milvus_host}:{milvus_port}"
        app_logger.info(f"初始化 Milvus vectorstore，URI: {milvus_uri}")

        # 构建连接参数
        vectorstore_connection_args = {"uri": milvus_uri}
        # 如果提供了用户名和密码,则添加到连接参数中
        if milvus_user and milvus_password:
            vectorstore_connection_args["user"] = milvus_user
            vectorstore_connection_args["password"] = milvus_password

        self.vectorstore = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args=vectorstore_connection_args,
            auto_id=True
        )

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )

        app_logger.info(f"RAG知识库初始化完成: {collection_name}")

    def add_documents(self, documents: List[Document], metadata: Optional[Dict] = None) -> List[str]:
        """
        添加文档到知识库

        Args:
            documents: 文档列表
            metadata: 额外的元数据

        Returns:
            文档ID列表
        """
        try:
            # 分割文档
            splits = self.text_splitter.split_documents(documents)

            # 添加元数据
            if metadata:
                for split in splits:
                    split.metadata.update(metadata)

            # 添加到向量数据库
            ids = self.vectorstore.add_documents(splits)

            app_logger.info(f"成功添加 {len(splits)} 个文档块到知识库")
            return ids

        except Exception as e:
            app_logger.error(f"添加文档失败: {str(e)}")
            raise

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[str]:
        """
        添加文本到知识库

        Args:
            texts: 文本列表
            metadatas: 元数据列表

        Returns:
            文档ID列表
        """
        try:
            # 分割文本
            all_splits = []
            for i, text in enumerate(texts):
                splits = self.text_splitter.split_text(text)
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}

                for split in splits:
                    all_splits.append(Document(page_content=split, metadata=metadata))

            # 添加到向量数据库
            ids = self.vectorstore.add_documents(all_splits)

            app_logger.info(f"成功添加 {len(all_splits)} 个文本块到知识库")
            return ids

        except Exception as e:
            app_logger.error(f"添加文本失败: {str(e)}")
            raise

    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            相关文档列表
        """
        try:
            results = self.vectorstore.similarity_search(query, k=top_k)
            app_logger.info(f"知识库搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            app_logger.error(f"知识库搜索失败: {str(e)}")
            return []

    def search_with_score(self, query: str, top_k: int = 5) -> List[tuple]:
        """
        搜索知识库并返回相似度分数

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            (文档, 分数) 元组列表
        """
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=top_k)
            app_logger.info(f"知识库搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            app_logger.error(f"知识库搜索失败: {str(e)}")
            return []

    def delete_collection(self):
        """删除整个知识库"""
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                app_logger.info(f"知识库已清空: {self.collection_name}")
            else:
                app_logger.warning(f"集合不存在: {self.collection_name}")
        except Exception as e:
            app_logger.error(f"清空知识库失败: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            if utility.has_collection(self.collection_name):
                collection = Collection(self.collection_name)
                collection.load()
                count = collection.num_entities
                return {
                    "total_documents": count,
                    "milvus_host": self.milvus_host,
                    "milvus_port": self.milvus_port,
                    "collection_name": self.collection_name,
                    "embedding_model": self.embedding_model
                }
            else:
                return {
                    "total_documents": 0,
                    "milvus_host": self.milvus_host,
                    "milvus_port": self.milvus_port,
                    "collection_name": self.collection_name,
                    "embedding_model": self.embedding_model,
                    "status": "collection_not_exists"
                }
        except Exception as e:
            app_logger.error(f"获取统计信息失败: {str(e)}")
            return {}


class RAGSearchTool(BaseTool):
    """RAG 知识库搜索工具"""

    name: str = "knowledge_base_search"
    description: str = """
    从知识库中搜索相关信息的工具。这是最重要的信息来源。

    【适用场景】（遇到以下任何场景都应该使用此工具）：
    1. 查询文档、手册、规范、标准等资料内容
    2. 查询API接口、功能说明、技术细节
    3. 查询产品功能、使用方法、操作步骤、配置说明
    4. 查询概念定义、术语解释、技术原理
    5. 查询历史记录、已存档的信息
    6. 任何需要准确、权威信息的查询
    7. 用户明确提到"文档"、"资料"、"知识库"等关键词
    8. 用户询问"如何"、"什么是"、"怎么做"等问题

    【输入格式】：
    - 输入应该是一个清晰的查询问题或关键词
    - 可以是完整的问题句子，如："如何配置API接口？"
    - 也可以是关键词组合，如："API配置 方法"

    【输出内容】：
    - 返回知识库中最相关的信息片段
    - 每个结果包含：内容、来源、相似度分数
    - 结果按相关性从高到低排序

    【使用建议】：
    - 在回答任何可能涉及已有文档的问题前，都应该先使用此工具
    - 即使不确定知识库中是否有相关信息，也建议先搜索一次
    - 搜索结果为空时，再考虑使用其他方式回答
    """

    knowledge_base: Any = Field(exclude=True)
    top_k: int = Field(default=5)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        """执行知识库搜索"""
        try:
            # 搜索知识库
            results = self.knowledge_base.search_with_score(query, top_k=self.top_k)

            if not results:
                return """【知识库搜索结果】
未在知识库中找到相关信息。

建议：
1. 尝试使用不同的关键词重新搜索
2. 如果这是新问题，可能需要先将相关文档添加到知识库
3. 可以基于通用知识回答，但需要明确告知用户信息来源不是知识库
"""

            # 格式化结果
            formatted_results = ["【知识库搜索结果】\n"]
            formatted_results.append(f"查询: {query}")
            formatted_results.append(f"找到 {len(results)} 条相关信息：\n")

            for i, (doc, score) in enumerate(results, 1):
                similarity = 1 - score
                source = doc.metadata.get("source", "未知来源")
                file_name = doc.metadata.get("file_name", "")
                content = doc.page_content.strip()

                # 根据相似度添加标记
                relevance_mark = ""
                if similarity >= 0.8:
                    relevance_mark = "【高度相关】"
                elif similarity >= 0.6:
                    relevance_mark = "【相关】"
                else:
                    relevance_mark = "【可能相关】"

                formatted_results.append(
                    f"\n{'='*60}\n"
                    f"[结果 {i}] {relevance_mark} (相似度: {similarity:.2%})\n"
                    f"来源: {source}"
                )

                if file_name:
                    formatted_results.append(f"文件: {file_name}")

                formatted_results.append(f"\n内容:\n{content}\n")

            formatted_results.append(f"\n{'='*60}")
            formatted_results.append("\n【使用说明】")
            formatted_results.append("- 请优先使用高相似度的结果回答用户问题")
            formatted_results.append("- 回答时请引用具体的来源信息")
            formatted_results.append("- 如果多个结果相关，可以综合使用")

            return "\n".join(formatted_results)

        except Exception as e:
            app_logger.error(f"知识库搜索失败: {str(e)}")
            return f"【知识库搜索失败】\n错误信息: {str(e)}\n请检查知识库连接或联系管理员。"

    async def _arun(self, query: str) -> str:
        """异步执行知识库搜索"""
        return self._run(query)


# 全局知识库实例
_knowledge_base_instance: Optional[RAGKnowledgeBase] = None


def get_knowledge_base() -> RAGKnowledgeBase:
    """获取全局知识库实例"""
    global _knowledge_base_instance

    if _knowledge_base_instance is None:
        _knowledge_base_instance = RAGKnowledgeBase(
            milvus_host=settings.rag_milvus_host,
            milvus_port=settings.rag_milvus_port,
            collection_name=settings.rag_milvus_collection,
            embedding_model=settings.rag_embedding_model,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            milvus_user=settings.rag_milvus_user,
            milvus_password=settings.rag_milvus_password
        )

    return _knowledge_base_instance


def create_rag_search_tool() -> RAGSearchTool:
    """创建 RAG 搜索工具"""
    kb = get_knowledge_base()
    return RAGSearchTool(
        knowledge_base=kb,
        top_k=settings.rag_top_k
    )

