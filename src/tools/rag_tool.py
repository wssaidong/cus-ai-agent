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
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
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
        chunk_overlap: int = 200
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
        """
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
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
            connections.connect(
                alias="default",
                host=milvus_host,
                port=milvus_port
            )
            app_logger.info(f"成功连接到 Milvus: {milvus_host}:{milvus_port}")
        except Exception as e:
            app_logger.error(f"连接 Milvus 失败: {str(e)}")
            raise

        # 初始化向量数据库
        self.vectorstore = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args={
                "host": milvus_host,
                "port": milvus_port
            },
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
    从知识库中搜索相关信息。
    输入应该是一个查询问题或关键词。
    返回知识库中最相关的信息。
    适用于需要查询文档、资料、知识点等场景。
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
                return "未在知识库中找到相关信息。"
            
            # 格式化结果
            formatted_results = []
            for i, (doc, score) in enumerate(results, 1):
                source = doc.metadata.get("source", "未知来源")
                content = doc.page_content.strip()
                formatted_results.append(
                    f"[结果 {i}] (相似度: {1-score:.2f})\n"
                    f"来源: {source}\n"
                    f"内容: {content}\n"
                )
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            app_logger.error(f"知识库搜索失败: {str(e)}")
            return f"知识库搜索失败: {str(e)}"
    
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
            chunk_overlap=settings.rag_chunk_overlap
        )

    return _knowledge_base_instance


def create_rag_search_tool() -> RAGSearchTool:
    """创建 RAG 搜索工具"""
    kb = get_knowledge_base()
    return RAGSearchTool(
        knowledge_base=kb,
        top_k=settings.rag_top_k
    )

