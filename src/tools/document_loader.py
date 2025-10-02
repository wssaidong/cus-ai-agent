"""
文档加载器模块
支持多种文档格式的加载
"""
import os
from typing import List, Optional
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from src.utils import app_logger


class DocumentLoader:
    """文档加载器"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.md': 'markdown',
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'docx'
    }
    
    @classmethod
    def load_file(cls, file_path: str, encoding: str = 'utf-8') -> List[Document]:
        """
        加载单个文件
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文档列表
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            extension = file_path.suffix.lower()
            
            if extension not in cls.SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"不支持的文件格式: {extension}。"
                    f"支持的格式: {', '.join(cls.SUPPORTED_EXTENSIONS.keys())}"
                )
            
            # 根据文件类型选择加载器
            if extension == '.txt':
                loader = TextLoader(str(file_path), encoding=encoding)
            elif extension == '.md':
                loader = UnstructuredMarkdownLoader(str(file_path))
            elif extension == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif extension in ['.docx', '.doc']:
                loader = Docx2txtLoader(str(file_path))
            else:
                raise ValueError(f"未实现的文件类型: {extension}")
            
            # 加载文档
            documents = loader.load()
            
            # 添加文件信息到元数据
            for doc in documents:
                doc.metadata.update({
                    'source': str(file_path),
                    'file_name': file_path.name,
                    'file_type': cls.SUPPORTED_EXTENSIONS[extension]
                })

            return documents
            
        except Exception as e:
            app_logger.error(f"加载文件失败 {file_path}: {str(e)}")
            raise
    
    @classmethod
    def load_directory(
        cls,
        directory_path: str,
        recursive: bool = True,
        encoding: str = 'utf-8'
    ) -> List[Document]:
        """
        加载目录中的所有支持的文件
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归加载子目录
            encoding: 文件编码
            
        Returns:
            文档列表
        """
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                raise FileNotFoundError(f"目录不存在: {directory_path}")
            
            if not directory_path.is_dir():
                raise ValueError(f"不是目录: {directory_path}")
            
            all_documents = []
            
            # 获取文件列表
            if recursive:
                files = directory_path.rglob('*')
            else:
                files = directory_path.glob('*')
            
            # 加载每个支持的文件
            for file_path in files:
                if file_path.is_file() and file_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS:
                    try:
                        documents = cls.load_file(str(file_path), encoding=encoding)
                        all_documents.extend(documents)
                    except Exception as e:
                        app_logger.warning(f"跳过文件 {file_path}: {str(e)}")
                        continue

            return all_documents
            
        except Exception as e:
            app_logger.error(f"加载目录失败 {directory_path}: {str(e)}")
            raise
    
    @classmethod
    def load_text(cls, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        从文本字符串创建文档
        
        Args:
            text: 文本内容
            metadata: 元数据
            
        Returns:
            文档列表
        """
        metadata = metadata or {}
        metadata.setdefault('source', 'text_input')
        metadata.setdefault('file_type', 'text')
        
        return [Document(page_content=text, metadata=metadata)]
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """获取支持的文件扩展名列表"""
        return list(cls.SUPPORTED_EXTENSIONS.keys())
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """检查文件是否支持"""
        extension = Path(file_path).suffix.lower()
        return extension in cls.SUPPORTED_EXTENSIONS

