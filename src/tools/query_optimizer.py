"""
查询优化器模块
用于优化知识库搜索查询，提升搜索准确度
"""
import re
from typing import List, Set, Dict
from src.utils import app_logger


class QueryOptimizer:
    """查询优化器 - 提升搜索准确度"""

    # 中文停用词
    CHINESE_STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '里', '就是', '什么', '怎么', '如何', '吗', '呢', '啊', '哦'
    }

    # 英文停用词
    ENGLISH_STOPWORDS = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'can', 'could', 'may', 'might', 'must', 'shall', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
        'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
        'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'but', 'or', 'and'
    }

    # 技术领域同义词映射
    SYNONYMS = {
        'api': ['接口', 'API', 'interface'],
        '接口': ['api', 'API', 'interface'],
        '配置': ['设置', '配置项', 'config', 'configuration', '参数'],
        '设置': ['配置', '配置项', 'config', 'configuration'],
        '方法': ['函数', 'method', 'function', '功能'],
        '函数': ['方法', 'method', 'function'],
        '错误': ['异常', 'error', 'exception', '问题', 'bug'],
        '异常': ['错误', 'error', 'exception'],
        '安装': ['部署', 'install', 'deploy', '配置'],
        '部署': ['安装', 'install', 'deploy'],
        '文档': ['资料', 'document', 'doc', '手册', 'manual'],
        '手册': ['文档', 'document', 'manual', '指南'],
        '指南': ['教程', 'guide', 'tutorial', '手册'],
        '教程': ['指南', 'guide', 'tutorial'],
        '数据库': ['db', 'database', '数据存储'],
        '服务器': ['server', '服务端', 'backend'],
        '客户端': ['client', '前端', 'frontend'],
    }

    def __init__(self):
        """初始化查询优化器"""
        self.stopwords = self.CHINESE_STOPWORDS | self.ENGLISH_STOPWORDS

    def optimize_query(self, query: str, expand_synonyms: bool = True) -> Dict[str, any]:
        """
        优化查询

        Args:
            query: 原始查询
            expand_synonyms: 是否扩展同义词

        Returns:
            优化结果字典，包含：
            - original_query: 原始查询
            - cleaned_query: 清理后的查询
            - keywords: 提取的关键词
            - expanded_terms: 扩展的同义词
            - optimized_query: 最终优化的查询
        """
        app_logger.info(f"[QueryOptimizer] 开始优化查询: {query}")

        # 1. 清理查询
        cleaned = self._clean_query(query)

        # 2. 提取关键词
        keywords = self._extract_keywords(cleaned)

        # 3. 扩展同义词
        expanded_terms = []
        if expand_synonyms:
            expanded_terms = self._expand_synonyms(keywords)

        # 4. 构建优化后的查询
        optimized = self._build_optimized_query(cleaned, keywords, expanded_terms)

        result = {
            'original_query': query,
            'cleaned_query': cleaned,
            'keywords': keywords,
            'expanded_terms': expanded_terms,
            'optimized_query': optimized
        }

        app_logger.info(f"[QueryOptimizer] 优化完成:")
        app_logger.info(f"  - 关键词: {keywords}")
        app_logger.info(f"  - 扩展词: {expanded_terms}")
        app_logger.info(f"  - 优化查询: {optimized}")

        return result

    def _clean_query(self, query: str) -> str:
        """
        清理查询文本
        - 去除多余空格
        - 统一标点符号
        - 去除特殊字符
        """
        # 去除多余空格
        cleaned = re.sub(r'\s+', ' ', query.strip())

        # 统一中文标点为英文标点
        cleaned = cleaned.replace('？', '?').replace('！', '!').replace('，', ',')
        cleaned = cleaned.replace('。', '.').replace('；', ';').replace('：', ':')

        # 去除多余的标点符号
        cleaned = re.sub(r'[?!.;:,]+$', '', cleaned)

        return cleaned

    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取关键词
        - 分词（简单基于空格和标点）
        - 去除停用词
        - 保留重要词汇
        """
        # 简单分词：基于空格和标点
        # 支持中英文混合
        # 先按空格分割
        parts = query.split()

        words = []
        for part in parts:
            # 对每个部分提取中英文词汇
            tokens = re.findall(r'[\w\u4e00-\u9fff]+', part)
            words.extend(tokens)

        # 如果没有空格分割的结果，直接提取所有词汇
        if not words:
            words = re.findall(r'[\w\u4e00-\u9fff]+', query)

        # 去除停用词和过短的词
        keywords = []
        for word in words:
            word_lower = word.lower()
            # 保留：非停用词 且 (长度>1 或 是英文单词)
            if word_lower not in self.stopwords:
                if len(word) > 1 or word.isalpha():
                    keywords.append(word)

        # 去重但保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        return unique_keywords

    def _expand_synonyms(self, keywords: List[str]) -> List[str]:
        """
        扩展同义词
        为关键词添加同义词，提升召回率
        """
        expanded = []

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 查找同义词
            if keyword_lower in self.SYNONYMS:
                synonyms = self.SYNONYMS[keyword_lower]
                for syn in synonyms:
                    # 避免重复
                    if syn.lower() not in [k.lower() for k in keywords]:
                        if syn not in expanded:
                            expanded.append(syn)

        return expanded

    def _build_optimized_query(
        self,
        cleaned: str,
        keywords: List[str],
        expanded_terms: List[str]
    ) -> str:
        """
        构建优化后的查询
        策略：保留原始查询的语义，同时增强关键词
        """
        # 如果有关键词，优先使用关键词组合
        if keywords:
            # 主查询：使用清理后的原始查询
            main_query = cleaned

            # 如果有扩展词，添加到查询中（用于提升召回）
            if expanded_terms:
                # 只添加最相关的2-3个扩展词，避免噪音
                top_expanded = expanded_terms[:3]
                enhanced_query = f"{main_query} {' '.join(top_expanded)}"
                return enhanced_query

            return main_query
        else:
            # 没有提取到关键词，使用原始清理后的查询
            return cleaned

    def generate_multi_queries(self, query: str) -> List[str]:
        """
        生成多个查询变体
        用于多次搜索以提升召回率

        Returns:
            查询变体列表
        """
        queries = []

        # 1. 原始查询
        queries.append(query)

        # 2. 优化后的查询
        optimized = self.optimize_query(query)
        if optimized['optimized_query'] != query:
            queries.append(optimized['optimized_query'])

        # 3. 仅关键词查询
        if optimized['keywords']:
            keyword_query = ' '.join(optimized['keywords'])
            if keyword_query not in queries:
                queries.append(keyword_query)

        # 4. 关键词+扩展词查询
        if optimized['keywords'] and optimized['expanded_terms']:
            all_terms = optimized['keywords'] + optimized['expanded_terms'][:2]
            expanded_query = ' '.join(all_terms)
            if expanded_query not in queries:
                queries.append(expanded_query)

        # 去重
        unique_queries = []
        seen = set()
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        app_logger.info(f"[QueryOptimizer] 生成 {len(unique_queries)} 个查询变体")
        return unique_queries

