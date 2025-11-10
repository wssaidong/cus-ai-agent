"""
搜索质量评估模块
评估搜索结果的质量，提供质量指标和改进建议
"""
from typing import List, Tuple, Dict
from langchain_core.documents import Document
from src.utils import app_logger


class SearchQualityEvaluator:
    """搜索质量评估器"""
    
    def __init__(self):
        """初始化评估器"""
        pass
    
    def evaluate(
        self,
        query: str,
        results: List[Tuple[Document, float]],
        keywords: List[str] = None
    ) -> Dict[str, any]:
        """
        评估搜索结果质量
        
        Args:
            query: 原始查询
            results: 搜索结果 [(Document, score), ...]
            keywords: 提取的关键词
            
        Returns:
            评估结果字典
        """
        if not results:
            return {
                'quality_score': 0.0,
                'quality_level': 'EMPTY',
                'result_count': 0,
                'avg_similarity': 0.0,
                'high_quality_count': 0,
                'recommendations': ['知识库中未找到相关信息，建议检查查询关键词或添加相关文档到知识库']
            }
        
        # 计算各项指标
        metrics = self._calculate_metrics(results, query, keywords)
        
        # 综合评分
        quality_score = self._compute_quality_score(metrics)
        
        # 质量等级
        quality_level = self._get_quality_level(quality_score)
        
        # 生成建议
        recommendations = self._generate_recommendations(metrics, quality_score)
        
        evaluation = {
            'quality_score': quality_score,
            'quality_level': quality_level,
            'result_count': len(results),
            'avg_similarity': metrics['avg_similarity'],
            'high_quality_count': metrics['high_quality_count'],
            'medium_quality_count': metrics['medium_quality_count'],
            'low_quality_count': metrics['low_quality_count'],
            'avg_keyword_coverage': metrics['avg_keyword_coverage'],
            'recommendations': recommendations,
            'metrics': metrics
        }
        
        app_logger.info(f"[SearchQuality] 质量评估: {quality_level} (得分: {quality_score:.2f})")
        
        return evaluation
    
    def _calculate_metrics(
        self,
        results: List[Tuple[Document, float]],
        query: str,
        keywords: List[str]
    ) -> Dict[str, any]:
        """计算评估指标"""
        metrics = {}
        
        # 相似度统计
        similarities = [1 - score for _, score in results]
        metrics['avg_similarity'] = sum(similarities) / len(similarities)
        metrics['max_similarity'] = max(similarities)
        metrics['min_similarity'] = min(similarities)
        
        # 质量分级统计
        metrics['high_quality_count'] = sum(1 for s in similarities if s >= 0.8)
        metrics['medium_quality_count'] = sum(1 for s in similarities if 0.6 <= s < 0.8)
        metrics['low_quality_count'] = sum(1 for s in similarities if s < 0.6)
        
        # 关键词覆盖率
        if keywords:
            keyword_coverages = []
            for doc, _ in results:
                content = doc.page_content.lower()
                matched = sum(1 for kw in keywords if kw.lower() in content)
                coverage = matched / len(keywords)
                keyword_coverages.append(coverage)
            
            metrics['avg_keyword_coverage'] = sum(keyword_coverages) / len(keyword_coverages)
            metrics['max_keyword_coverage'] = max(keyword_coverages)
        else:
            metrics['avg_keyword_coverage'] = 0.0
            metrics['max_keyword_coverage'] = 0.0
        
        # 内容长度统计
        content_lengths = [len(doc.page_content) for doc, _ in results]
        metrics['avg_content_length'] = sum(content_lengths) / len(content_lengths)
        
        # 元数据完整性
        metadata_scores = []
        for doc, _ in results:
            score = 0
            if doc.metadata.get('file_name'):
                score += 0.25
            if doc.metadata.get('source'):
                score += 0.25
            if doc.metadata.get('file_type'):
                score += 0.25
            if doc.metadata.get('upload_time'):
                score += 0.25
            metadata_scores.append(score)
        
        metrics['avg_metadata_completeness'] = sum(metadata_scores) / len(metadata_scores)
        
        return metrics
    
    def _compute_quality_score(self, metrics: Dict[str, any]) -> float:
        """
        计算综合质量得分
        
        权重分配：
        - 平均相似度: 40%
        - 高质量结果占比: 30%
        - 关键词覆盖率: 20%
        - 元数据完整性: 10%
        """
        score = 0.0
        
        # 平均相似度得分
        score += metrics['avg_similarity'] * 0.4
        
        # 高质量结果占比
        total_count = (
            metrics['high_quality_count'] + 
            metrics['medium_quality_count'] + 
            metrics['low_quality_count']
        )
        if total_count > 0:
            high_quality_ratio = metrics['high_quality_count'] / total_count
            score += high_quality_ratio * 0.3
        
        # 关键词覆盖率
        score += metrics['avg_keyword_coverage'] * 0.2
        
        # 元数据完整性
        score += metrics['avg_metadata_completeness'] * 0.1
        
        return min(1.0, score)
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 0.8:
            return 'EXCELLENT'  # 优秀
        elif score >= 0.6:
            return 'GOOD'       # 良好
        elif score >= 0.4:
            return 'FAIR'       # 一般
        elif score >= 0.2:
            return 'POOR'       # 较差
        else:
            return 'VERY_POOR'  # 很差
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, any],
        quality_score: float
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于平均相似度
        if metrics['avg_similarity'] < 0.6:
            recommendations.append(
                f"搜索结果平均相似度较低（{metrics['avg_similarity']:.1%}），"
                "建议尝试使用不同的关键词或更具体的查询"
            )
        
        # 基于高质量结果数量
        if metrics['high_quality_count'] == 0:
            recommendations.append(
                "未找到高相关度（≥80%）的结果，建议调整查询或检查知识库内容"
            )
        elif metrics['high_quality_count'] < 2:
            recommendations.append(
                f"仅找到 {metrics['high_quality_count']} 个高相关度结果，"
                "可能需要补充更多相关文档到知识库"
            )
        
        # 基于关键词覆盖率
        if metrics['avg_keyword_coverage'] < 0.5:
            recommendations.append(
                f"关键词覆盖率较低（{metrics['avg_keyword_coverage']:.1%}），"
                "结果可能不够精准，建议使用更准确的关键词"
            )
        
        # 基于内容长度
        if metrics['avg_content_length'] < 100:
            recommendations.append(
                "搜索结果内容较短，可能信息不够完整，建议查看更多结果或调整查询"
            )
        
        # 基于元数据完整性
        if metrics['avg_metadata_completeness'] < 0.5:
            recommendations.append(
                "部分结果缺少元数据信息，建议在上传文档时添加完整的元数据"
            )
        
        # 如果没有具体建议，给出通用建议
        if not recommendations:
            if quality_score >= 0.8:
                recommendations.append("搜索结果质量优秀，可以直接使用")
            else:
                recommendations.append("搜索结果质量良好，建议综合多个结果使用")
        
        return recommendations
    
    def should_use_results(self, evaluation: Dict[str, any]) -> bool:
        """
        判断是否应该使用搜索结果
        
        Args:
            evaluation: 评估结果
            
        Returns:
            是否应该使用结果
        """
        # 质量得分阈值
        if evaluation['quality_score'] < 0.3:
            app_logger.warning(
                f"[SearchQuality] 搜索结果质量过低 ({evaluation['quality_score']:.2f})，"
                "不建议使用"
            )
            return False
        
        # 至少要有一个中等质量以上的结果
        if evaluation['high_quality_count'] == 0 and evaluation['medium_quality_count'] == 0:
            app_logger.warning(
                "[SearchQuality] 没有中等质量以上的结果，不建议使用"
            )
            return False
        
        return True
    
    def format_quality_report(self, evaluation: Dict[str, any]) -> str:
        """
        格式化质量报告
        
        Args:
            evaluation: 评估结果
            
        Returns:
            格式化的报告文本
        """
        level_names = {
            'EXCELLENT': '优秀',
            'GOOD': '良好',
            'FAIR': '一般',
            'POOR': '较差',
            'VERY_POOR': '很差',
            'EMPTY': '无结果'
        }
        
        report = [
            "\n【搜索质量评估】",
            f"质量等级: {level_names.get(evaluation['quality_level'], '未知')}",
            f"综合得分: {evaluation['quality_score']:.1%}",
            f"结果数量: {evaluation['result_count']}",
            f"平均相似度: {evaluation['avg_similarity']:.1%}",
            f"高质量结果: {evaluation['high_quality_count']} 个（相似度≥80%）",
            f"中等质量结果: {evaluation['medium_quality_count']} 个（相似度60-80%）",
            f"低质量结果: {evaluation['low_quality_count']} 个（相似度<60%）",
        ]
        
        if evaluation['recommendations']:
            report.append("\n【改进建议】")
            for i, rec in enumerate(evaluation['recommendations'], 1):
                report.append(f"{i}. {rec}")
        
        return "\n".join(report)

