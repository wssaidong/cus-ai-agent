"""
知识库管理 API 路由
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import tempfile
import os
import json
from datetime import datetime
from src.tools.rag_tool import get_knowledge_base
from src.tools.document_loader import DocumentLoader
from src.utils import app_logger


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

# 常量定义
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TEXT_LENGTH = 1000000  # 1M 字符
ALLOWED_CATEGORIES = [
    "技术文档", "用户指南", "故障排查", "经验总结", "业务文档",
    "api", "architecture", "deployment", "configuration",
    "quickstart", "faq", "best_practice", "troubleshooting",
    "solution", "feedback", "agent_experience"
]


class DocumentMetadata(BaseModel):
    """文档元数据模型"""
    title: Optional[str] = Field(None, description="文档标题")
    category: Optional[str] = Field(None, description="文档分类")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    source: Optional[str] = Field(None, description="文档来源")
    author: Optional[str] = Field(None, description="文档作者")
    version: Optional[str] = Field(None, description="文档版本")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")

    @validator('category')
    def validate_category(cls, v):
        if v and v not in ALLOWED_CATEGORIES:
            raise ValueError(f"分类必须是以下之一: {', '.join(ALLOWED_CATEGORIES)}")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in ['high', 'medium', 'low']:
            raise ValueError("优先级必须是: high, medium 或 low")
        return v


class AddTextRequest(BaseModel):
    """添加文本请求"""
    text: str = Field(..., description="文本内容", min_length=1, max_length=MAX_TEXT_LENGTH)
    metadata: Optional[DocumentMetadata] = Field(None, description="文档元数据")

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("文本内容不能为空")
        return v


class WriteExperienceRequest(BaseModel):
    """写入经验请求"""
    content: str = Field(..., description="内容", min_length=1, max_length=MAX_TEXT_LENGTH)
    title: Optional[str] = Field(None, description="标题")
    category: Optional[str] = Field("agent_experience", description="分类")
    tags: Optional[str] = Field(None, description="标签")
    source: Optional[str] = Field("agent_experience", description="来源")


class UpdateExperienceRequest(BaseModel):
    """更新经验请求"""
    content: str = Field(..., description="内容", min_length=1, max_length=MAX_TEXT_LENGTH)
    title: Optional[str] = Field(None, description="标题")
    category: Optional[str] = Field("agent_experience", description="分类")
    tags: Optional[str] = Field(None, description="标签")
    reason: Optional[str] = Field(None, description="更新原因")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询", min_length=1)
    top_k: int = Field(5, description="返回结果数", ge=1, le=100)


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[dict] = Field(..., description="搜索结果")
    total: int = Field(..., description="结果总数")


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    document_count: int = Field(..., description="文档数量")
    chunk_count: int = Field(..., description="分块数量")
    document_ids: List[Any] = Field(..., description="文档ID列表")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")
    upload_time: str = Field(..., description="上传时间")


@router.post("/upload", summary="上传文档到知识库", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    version: Optional[str] = Form("1.0"),
    priority: Optional[str] = Form(None)
):
    """
    上传文档到知识库

    支持的文件格式: .txt, .md, .pdf, .docx, .doc

    **参数说明**:
    - file: 要上传的文件
    - category: 文档分类 (可选)
    - tags: 标签，逗号分隔 (可选)
    - source: 文档来源 (可选)
    - author: 文档作者 (可选)
    - version: 文档版本 (默认: 1.0)
    - priority: 优先级 high/medium/low (可选)

    **返回**:
    - success: 是否成功
    - message: 响应消息
    - document_count: 文档数量
    - chunk_count: 分块数量
    - document_ids: 文档ID列表
    - file_name: 文件名
    - file_size: 文件大小
    - upload_time: 上传时间
    """
    tmp_file_path = None
    try:
        # 1. 验证文件名
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 2. 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not DocumentLoader.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_extension}。"
                       f"支持的格式: {', '.join(DocumentLoader.get_supported_extensions())}"
            )

        # 3. 读取文件内容
        content = await file.read()
        file_size = len(content)

        # 4. 检查文件大小
        if file_size == 0:
            raise HTTPException(status_code=400, detail="文件为空")

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大。最大允许大小: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )

        # 5. 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # 6. 加载文档
        documents = DocumentLoader.load_file(tmp_file_path)

        if not documents:
            raise HTTPException(status_code=400, detail="文档加载失败或文档为空")

        # 7. 构建元数据
        extra_metadata = {
            'uploaded_filename': file.filename,
            'file_size': file_size,
            'upload_time': datetime.now().isoformat(),
            'file_type': DocumentLoader.SUPPORTED_EXTENSIONS.get(file_extension, 'unknown'),
            'version': version or '1.0'
        }

        # 添加可选元数据
        if category:
            if category not in ALLOWED_CATEGORIES:
                app_logger.warning(f"未知的分类: {category}")
            extra_metadata['category'] = category

        if tags:
            extra_metadata['tags'] = tags

        if source:
            extra_metadata['source'] = source

        if author:
            extra_metadata['author'] = author

        if priority and priority in ['high', 'medium', 'low']:
            extra_metadata['priority'] = priority

        # 8. 添加到知识库
        kb = get_knowledge_base()
        ids = kb.add_documents(documents, metadata=extra_metadata)

        if not ids:
            raise HTTPException(status_code=500, detail="添加文档到知识库失败")

        app_logger.info(
            f"成功上传文档: {file.filename}, "
            f"文档数: {len(documents)}, 分块数: {len(ids)}"
        )

        # 转换 IDs 为字符串
        document_ids = [str(id) for id in ids[:10]]

        return UploadResponse(
            success=True,
            message=f"成功上传文档: {file.filename}",
            document_count=len(documents),
            chunk_count=len(ids),
            document_ids=document_ids,
            file_name=file.filename,
            file_size=file_size,
            upload_time=extra_metadata['upload_time']
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"上传文档失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")

    finally:
        # 清理临时文件
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                app_logger.warning(f"删除临时文件失败: {str(e)}")


@router.post("/add-text", summary="添加文本到知识库")
async def add_text(request: AddTextRequest):
    """
    直接添加文本到知识库

    **参数说明**:
    - text: 文本内容 (必需)
    - metadata: 文档元数据 (可选)
      - title: 文档标题
      - category: 文档分类
      - tags: 标签
      - source: 来源
      - author: 作者
      - version: 版本
      - priority: 优先级

    **返回**:
    - success: 是否成功
    - message: 响应消息
    - document_ids: 文档ID列表
    - chunk_count: 分块数量
    """
    try:
        # 1. 验证文本
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 2. 构建元数据
        metadata_dict = {
            'upload_time': datetime.now().isoformat(),
            'source': 'api_add_text'
        }

        if request.metadata:
            if request.metadata.title:
                metadata_dict['title'] = request.metadata.title
            if request.metadata.category:
                metadata_dict['category'] = request.metadata.category
            if request.metadata.tags:
                metadata_dict['tags'] = request.metadata.tags
            if request.metadata.source:
                metadata_dict['source'] = request.metadata.source
            if request.metadata.author:
                metadata_dict['author'] = request.metadata.author
            if request.metadata.version:
                metadata_dict['version'] = request.metadata.version
            if request.metadata.priority:
                metadata_dict['priority'] = request.metadata.priority

        # 3. 创建文档
        documents = DocumentLoader.load_text(request.text, metadata=metadata_dict)

        # 4. 添加到知识库
        kb = get_knowledge_base()
        ids = kb.add_documents(documents)

        if not ids:
            raise HTTPException(status_code=500, detail="添加文本到知识库失败")

        app_logger.info(f"成功添加文本到知识库, 分块数: {len(ids)}")

        # 转换 IDs 为字符串
        document_ids = [str(id) for id in ids]

        return {
            "success": True,
            "message": "成功添加文本到知识库",
            "document_ids": document_ids,
            "chunk_count": len(ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"添加文本失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加文本失败: {str(e)}")


@router.post("/search", response_model=SearchResponse, summary="搜索知识库")
async def search_knowledge(request: SearchRequest):
    """
    搜索知识库

    **参数说明**:
    - query: 搜索查询 (必需)
    - top_k: 返回结果数 (默认: 5, 范围: 1-100)

    **返回**:
    - results: 搜索结果列表
      - content: 文档内容
      - metadata: 文档元数据
      - similarity_score: 相似度分数 (0-1)
    - total: 结果总数
    """
    try:
        # 1. 验证查询
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="搜索查询不能为空")

        # 2. 执行搜索
        kb = get_knowledge_base()
        results = kb.search_with_score(request.query, top_k=request.top_k)

        # 3. 格式化结果
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(1 - score)  # 转换为相似度分数
            })

        app_logger.info(f"搜索完成: 查询='{request.query}', 结果数={len(formatted_results)}")

        return SearchResponse(
            results=formatted_results,
            total=len(formatted_results)
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"搜索知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/stats", summary="获取知识库统计信息")
async def get_stats():
    """
    获取知识库统计信息

    **返回**:
    - success: 是否成功
    - stats: 统计信息
      - total_documents: 文档总数
      - total_chunks: 分块总数
      - collection_name: 集合名称
      - 其他统计信息
    """
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()

        app_logger.info(f"获取统计信息: {stats}")

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        app_logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/clear", summary="清空知识库")
async def clear_knowledge_base():
    """
    清空整个知识库

    ⚠️ **警告**: 此操作不可逆，将删除所有知识库数据！

    **返回**:
    - success: 是否成功
    - message: 响应消息
    - timestamp: 操作时间
    """
    try:
        kb = get_knowledge_base()
        kb.delete_collection()

        app_logger.warning("知识库已清空")

        return {
            "success": True,
            "message": "知识库已清空",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        app_logger.error(f"清空知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@router.get("/supported-formats", summary="获取支持的文件格式")
async def get_supported_formats():
    """
    获取支持的文件格式列表

    **返回**:
    - formats: 支持的文件扩展名列表
    - descriptions: 文件格式描述
    - max_file_size: 最大文件大小 (字节)
    - max_text_length: 最大文本长度 (字符)
    - categories: 支持的分类列表
    """
    return {
        "formats": DocumentLoader.get_supported_extensions(),
        "descriptions": {
            ".txt": "纯文本文件",
            ".md": "Markdown 文件",
            ".pdf": "PDF 文档",
            ".docx": "Word 文档",
            ".doc": "Word 文档 (旧版)"
        },
        "max_file_size": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "max_text_length": MAX_TEXT_LENGTH,
        "categories": ALLOWED_CATEGORIES,
        "priorities": ["high", "medium", "low"]
    }


@router.post("/write-experience", summary="写入智能体经验到知识库")
async def write_experience(request: WriteExperienceRequest):
    """
    将智能体的经验、解决方案等写入到知识库

    - **content**: 要写入的内容（必需）
    - **title**: 内容标题（可选）
    - **category**: 内容分类，如 solution, best_practice, faq, architecture, feedback（可选）
    - **tags**: 标签列表，用逗号分隔（可选）
    - **source**: 内容来源，如 agent_experience, user_feedback（可选）
    """
    try:
        from datetime import datetime

        # 构建元数据 - 包含所有 Milvus 必需字段
        metadata = {
            "title": request.title or "无标题",
            "category": request.category,
            "tags": request.tags or "",
            "source": request.source,
            "timestamp": datetime.now().isoformat(),
            "type": "agent_experience",
            "file_name": request.title or "agent_experience",
            "file_type": "agent_experience",  # Milvus 必需字段
            "version": "1.0",  # Milvus 必需字段
            "author": "agent",  # Milvus 必需字段
            "uploaded_filename": request.title or "agent_experience"  # Milvus 必需字段
        }

        # 获取知识库实例
        kb = get_knowledge_base()

        # 添加到知识库
        ids = kb.add_texts([request.content], metadatas=[metadata])

        if ids:
            app_logger.info(f"成功写入经验到知识库: {request.title or '无标题'}")
            return {
                "success": True,
                "message": "成功写入经验到知识库",
                "document_id": ids[0],
                "title": request.title or "无标题",
                "category": request.category,
                "timestamp": metadata["timestamp"]
            }
        else:
            raise Exception("写入失败，未返回文档ID")

    except Exception as e:
        app_logger.error(f"写入经验失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"写入经验失败: {str(e)}")


@router.post("/update-experience", summary="更新知识库中的经验")
async def update_experience(request: UpdateExperienceRequest):
    """
    更新知识库中已有的经验内容

    - **content**: 更新后的内容（必需）
    - **title**: 内容标题（可选）
    - **category**: 内容分类（可选）
    - **tags**: 标签列表（可选）
    - **reason**: 更新原因（可选）
    """
    try:
        from datetime import datetime

        # 构建元数据 - 包含所有 Milvus 必需字段
        metadata = {
            "title": request.title or "无标题",
            "category": request.category,
            "tags": request.tags or "",
            "source": "agent_update",
            "timestamp": datetime.now().isoformat(),
            "type": "agent_experience",
            "update_reason": request.reason or "",
            "file_name": request.title or "agent_update",
            "file_type": "agent_update",  # Milvus 必需字段
            "version": "1.0",  # Milvus 必需字段
            "author": "agent",  # Milvus 必需字段
            "uploaded_filename": request.title or "agent_update"  # Milvus 必需字段
        }

        # 获取知识库实例
        kb = get_knowledge_base()

        # 添加更新的内容（作为新文档）
        ids = kb.add_texts([request.content], metadatas=[metadata])

        if ids:
            app_logger.info(f"成功更新知识库: {request.title or '无标题'}")
            return {
                "success": True,
                "message": "成功更新知识库",
                "document_id": ids[0],
                "title": request.title or "无标题",
                "category": request.category,
                "update_reason": request.reason or "",
                "timestamp": metadata["timestamp"]
            }
        else:
            raise Exception("更新失败，未返回文档ID")

    except Exception as e:
        app_logger.error(f"更新经验失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新经验失败: {str(e)}")

