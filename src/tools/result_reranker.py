"""
搜索结果重排序模块
基于多个维度对搜索结果进行重新排序，提升准确度
"""
import re
from typing import List, Tuple, Dict
from langchain_core.documents import Document
from src.utils import app_logger


class ResultReranker:
    """搜索结果重排序器"""
    
    def __init__(self):
        """初始化重排序器"""
        pass
    
    def rerank(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        keywords: List[str] = None
    ) -> List[Tuple[Document, float]]:
        """
        重新排序搜索结果
        
        Args:
            results: 原始搜索结果 [(Document, score), ...]
            query: 原始查询
            keywords: 提取的关键词列表
            
        Returns:
            重新排序后的结果
        """
        if not results:
            return results
        
        app_logger.info(f"[ResultReranker] 开始重排序 {len(results)} 个结果")
        
        # 计算每个结果的综合得分
        scored_results = []
        for doc, original_score in results:
            # 计算多维度得分
            scores = self._calculate_scores(doc, query, keywords, original_score)
            
            # 综合得分（加权平均）
            final_score = self._compute_final_score(scores)
            
            scored_results.append((doc, original_score, final_score, scores))
        
        # 按综合得分排序（降序）
        scored_results.sort(key=lambda x: x[2], reverse=True)
        
        # 记录排序变化
        self._log_reranking(scored_results)
        
        # 返回重排序后的结果（保持原始格式）
        reranked = [(doc, original_score) for doc, original_score, _, _ in scored_results]
        
        return reranked
    
    def _calculate_scores(
        self,
        doc: Document,
        query: str,
        keywords: List[str],
        original_score: float
    ) -> Dict[str, float]:
        """
        计算多维度得分
        
        Returns:
            各维度得分字典
        """
        content = doc.page_content.lower()
        query_lower = query.lower()
        
        scores = {}
        
        # 1. 向量相似度得分（原始得分，转换为0-1）
        scores['vector_similarity'] = 1 - original_score
        
        # 2. 关键词匹配得分
        scores['keyword_match'] = self._keyword_match_score(content, keywords or [])
        
        # 3. 查询词完整匹配得分
        scores['exact_match'] = self._exact_match_score(content, query_lower)
        
        # 4. 内容长度得分（适中长度更好）
        scores['content_length'] = self._content_length_score(content)
        
        # 5. 元数据质量得分
        scores['metadata_quality'] = self._metadata_quality_score(doc.metadata)
        
        # 6. 位置得分（关键词出现位置）
        scores['position'] = self._position_score(content, query_lower, keywords or [])
        
        return scores
    
    def _keyword_match_score(self, content: str, keywords: List[str]) -> float:
        """
        关键词匹配得分
        计算关键词在内容中的覆盖率
        """
        if not keywords:
            return 0.5  # 中性得分
        
        matched = 0
        for keyword in keywords:
            if keyword.lower() in content:
                matched += 1
        
        # 匹配率
        match_rate = matched / len(keywords)
        
        # 额外奖励：多个关键词同时出现
        if match_rate >= 0.8:
            return min(1.0, match_rate + 0.1)
        
        return match_rate
    
    def _exact_match_score(self, content: str, query: str) -> float:
        """
        完整查询匹配得分
        查询词作为整体出现在内容中
        """
        if not query:
            return 0.0
        
        # 完全匹配
        if query in content:
            return 1.0
        
        # 部分匹配（查询词的连续子串）
        query_words = query.split()
        if len(query_words) <= 1:
            return 0.0
        
        # 检查连续的词组
        max_match = 0
        for i in range(len(query_words)):
            for j in range(i + 2, len(query_words) + 1):
                phrase = ' '.join(query_words[i:j])
                if phrase in content:
                    match_len = j - i
                    max_match = max(max_match, match_len)
        
        # 部分匹配得分
        if max_match > 0:
            return 0.5 + (0.5 * max_match / len(query_words))
        
        return 0.0
    
    def _content_length_score(self, content: str) -> float:
        """
        内容长度得分
        适中长度的内容通常质量更好
        """
        length = len(content)
        
        # 理想长度范围：200-2000字符
        if 200 <= length <= 2000:
            return 1.0
        elif length < 200:
            # 太短，可能信息不完整
            return 0.5 + (length / 400)
        else:
            # 太长，可能包含无关信息
            return max(0.3, 1.0 - (length - 2000) / 10000)
    
    def _metadata_quality_score(self, metadata: Dict) -> float:
        """
        元数据质量得分
        有完整元数据的文档通常质量更好
        """
        score = 0.5  # 基础分
        
        # 有文件名
        if metadata.get('file_name'):
            score += 0.2
        
        # 有来源
        if metadata.get('source'):
            score += 0.1
        
        # 有文件类型
        if metadata.get('file_type'):
            score += 0.1
        
        # 有上传时间
        if metadata.get('upload_time'):
            score += 0.1
        
        return min(1.0, score)
    
    def _position_score(
        self,
        content: str,
        query: str,
        keywords: List[str]
    ) -> float:
        """
        位置得分
        关键词出现在文档开头的得分更高
        """
        # 检查前300个字符
        prefix = content[:300]
        
        score = 0.5  # 基础分
        
        # 查询词在前面出现
        if query and query in prefix:
            score += 0.3
        
        # 关键词在前面出现
        if keywords:
            early_keywords = sum(1 for kw in keywords if kw.lower() in prefix)
            if early_keywords > 0:
                score += 0.2 * (early_keywords / len(keywords))
        
        return min(1.0, score)
    
    def _compute_final_score(self, scores: Dict[str, float]) -> float:
        """
        计算最终综合得分
        使用加权平均
        """
        # 权重配置（可调整）
        weights = {
            'vector_similarity': 0.30,   # 向量相似度 30%
            'keyword_match': 0.25,       # 关键词匹配 25%
            'exact_match': 0.20,         # 完整匹配 20%
            'content_length': 0.10,      # 内容长度 10%
            'metadata_quality': 0.05,    # 元数据质量 5%
            'position': 0.10,            # 位置得分 10%
        }
        
        final_score = 0.0
        for dimension, weight in weights.items():
            final_score += scores.get(dimension, 0.0) * weight
        
        return final_score
    
    def _log_reranking(self, scored_results: List[Tuple]):
        """记录重排序结果"""
        app_logger.info(f"[ResultReranker] 重排序完成，前3个结果:")
        
        for i, (doc, original_score, final_score, scores) in enumerate(scored_results[:3], 1):
            content_preview = doc.page_content[:50].replace('\n', ' ')
            app_logger.info(
                f"  [{i}] 原始分数: {1-original_score:.3f} -> 综合分数: {final_score:.3f}"
            )
            app_logger.info(f"      内容: {content_preview}...")
            app_logger.debug(f"      详细得分: {scores}")
    
    def filter_low_quality(
        self,
        results: List[Tuple[Document, float]],
        min_score: float = 0.3
    ) -> List[Tuple[Document, float]]:
        """
        过滤低质量结果
        
        Args:
            results: 搜索结果
            min_score: 最低综合得分阈值
            
        Returns:
            过滤后的结果
        """
        if not results:
            return results
        
        # 这里的score是重排序后的综合得分
        # 如果需要过滤，需要先重排序
        filtered = [
            (doc, score) for doc, score in results
            if (1 - score) >= min_score  # score是距离，1-score是相似度
        ]
        
        removed = len(results) - len(filtered)
        if removed > 0:
            app_logger.info(f"[ResultReranker] 过滤掉 {removed} 个低质量结果")
        
        return filtered

