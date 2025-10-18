"""
知识库管理 API 路由
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import tempfile
import os
from src.tools.rag_tool import get_knowledge_base
from src.tools.document_loader import DocumentLoader
from src.utils import app_logger


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class AddTextRequest(BaseModel):
    """添加文本请求"""
    text: str
    metadata: Optional[dict] = None


class WriteExperienceRequest(BaseModel):
    """写入经验请求"""
    content: str
    title: Optional[str] = None
    category: Optional[str] = "agent_experience"
    tags: Optional[str] = None
    source: Optional[str] = "agent_experience"


class UpdateExperienceRequest(BaseModel):
    """更新经验请求"""
    content: str
    title: Optional[str] = None
    category: Optional[str] = "agent_experience"
    tags: Optional[str] = None
    reason: Optional[str] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[dict]
    total: int


@router.post("/upload", summary="上传文档到知识库")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """
    上传文档到知识库

    支持的文件格式: .txt, .md, .pdf, .docx, .doc
    """
    try:
        # 检查文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not DocumentLoader.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_extension}。"
                       f"支持的格式: {', '.join(DocumentLoader.get_supported_extensions())}"
            )

        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # 加载文档
            documents = DocumentLoader.load_file(tmp_file_path)

            # 解析元数据
            import json
            extra_metadata = {}
            if metadata:
                try:
                    extra_metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    app_logger.warning(f"无效的元数据JSON: {metadata}")

            extra_metadata['uploaded_filename'] = file.filename

            # 添加到知识库
            kb = get_knowledge_base()
            ids = kb.add_documents(documents, metadata=extra_metadata)

            return {
                "success": True,
                "message": f"成功上传文档: {file.filename}",
                "document_count": len(documents),
                "chunk_count": len(ids),
                "document_ids": ids[:10]  # 只返回前10个ID
            }

        finally:
            # 删除临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except Exception as e:
        app_logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.post("/add-text", summary="添加文本到知识库")
async def add_text(request: AddTextRequest):
    """
    直接添加文本到知识库
    """
    try:
        # 创建文档
        documents = DocumentLoader.load_text(request.text, metadata=request.metadata)

        # 添加到知识库
        kb = get_knowledge_base()
        ids = kb.add_documents(documents)

        return {
            "success": True,
            "message": "成功添加文本到知识库",
            "document_ids": ids
        }

    except Exception as e:
        app_logger.error(f"添加文本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加文本失败: {str(e)}")


@router.post("/search", response_model=SearchResponse, summary="搜索知识库")
async def search_knowledge(request: SearchRequest):
    """
    搜索知识库
    """
    try:
        kb = get_knowledge_base()
        results = kb.search_with_score(request.query, top_k=request.top_k)

        # 格式化结果
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(1 - score)  # 转换为相似度分数
            })

        return SearchResponse(
            results=formatted_results,
            total=len(formatted_results)
        )

    except Exception as e:
        app_logger.error(f"搜索知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/stats", summary="获取知识库统计信息")
async def get_stats():
    """
    获取知识库统计信息
    """
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        app_logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/clear", summary="清空知识库")
async def clear_knowledge_base():
    """
    清空整个知识库

    警告: 此操作不可逆!
    """
    try:
        kb = get_knowledge_base()
        kb.delete_collection()

        return {
            "success": True,
            "message": "知识库已清空"
        }

    except Exception as e:
        app_logger.error(f"清空知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@router.get("/supported-formats", summary="获取支持的文件格式")
async def get_supported_formats():
    """
    获取支持的文件格式列表
    """
    return {
        "formats": DocumentLoader.get_supported_extensions(),
        "descriptions": {
            ".txt": "纯文本文件",
            ".md": "Markdown 文件",
            ".pdf": "PDF 文档",
            ".docx": "Word 文档",
            ".doc": "Word 文档 (旧版)"
        }
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

