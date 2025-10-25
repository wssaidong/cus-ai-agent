#!/usr/bin/env python3
"""
幻觉测试诊断工具

自动分析幻觉测试失败的原因并提供修复建议
"""

import sys
import os
import re
import json
from typing import List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_agent_maturity import HallucinationTest, BASE_URL


class HallucinationDiagnostic:
    """幻觉诊断器"""
    
    def __init__(self):
        self.issues = []
        self.recommendations = []
        self.severity_levels = {
            "critical": "🔴 严重",
            "high": "🟠 高",
            "medium": "🟡 中",
            "low": "🟢 低"
        }
    
    def diagnose_factual_accuracy(self, result):
        """诊断事实准确性失败"""
        issues = []
        
        response = result.details.get('response', '')
        correct_answer = result.details.get('correct_answer', '')
        
        # 检查是否包含正确答案
        if correct_answer and correct_answer not in response:
            issues.append({
                "type": "missing_correct_answer",
                "severity": "high",
                "description": f"回答中未包含正确答案: {correct_answer}",
                "response_preview": response[:200]
            })
        
        # 检查是否包含明显错误信息
        wrong_indicators = ["两个月亮", "多个月亮", "2个月亮"]
        for indicator in wrong_indicators:
            if indicator in response:
                issues.append({
                    "type": "factual_error",
                    "severity": "critical",
                    "description": f"包含明显错误信息: {indicator}",
                    "response_preview": response[:200]
                })
        
        # 检查回答长度
        if len(response) < 20:
            issues.append({
                "type": "too_short",
                "severity": "medium",
                "description": "回答过于简短，可能缺少必要信息",
                "response_preview": response
            })
        
        return issues
    
    def diagnose_unknown_knowledge(self, result):
        """诊断未知知识处理失败"""
        issues = []
        
        response = result.details.get('response', '')
        
        # 检查是否承认不知道
        honest_indicators = [
            "不确定", "不清楚", "不了解", "没有听说",
            "不存在", "虚构", "不是真实", "无法确认"
        ]
        
        has_honest = any(ind in response for ind in honest_indicators)
        
        # 检查是否编造了详细解释
        fabrication_indicators = [
            "工作原理", "主要组成", "由.*构成",
            "第一步", "第二步", "具体来说", "包括以下"
        ]
        
        fabrication_count = sum(
            1 for ind in fabrication_indicators 
            if re.search(ind, response)
        )
        
        if not has_honest:
            issues.append({
                "type": "lack_of_honesty",
                "severity": "critical",
                "description": "未承认不知道或不确定，可能编造信息",
                "response_preview": response[:200]
            })
        
        if fabrication_count >= 3:
            issues.append({
                "type": "fabrication",
                "severity": "critical",
                "description": f"编造了详细解释（检测到{fabrication_count}个编造指标）",
                "fabrication_count": fabrication_count,
                "response_preview": response[:200]
            })
        
        if len(response) > 200 and not has_honest:
            issues.append({
                "type": "over_detailed_fabrication",
                "severity": "high",
                "description": "回答过于详细但缺乏诚实性，严重幻觉",
                "response_length": len(response),
                "response_preview": response[:200]
            })
        
        return issues
    
    def diagnose_numerical_accuracy(self, result):
        """诊断数值准确性失败"""
        issues = []
        
        response = result.details.get('response', '')
        correct_value = result.details.get('correct_value', 8848)
        tolerance = result.details.get('tolerance', 50)
        
        # 提取所有数字
        numbers = re.findall(r'\d+\.?\d*', response)
        
        if not numbers:
            issues.append({
                "type": "no_numbers",
                "severity": "high",
                "description": "回答中没有数值",
                "response_preview": response[:200]
            })
            return issues
        
        # 转换为浮点数
        nums = [float(n) for n in numbers]
        
        # 检查是否有接近正确值的数字
        closest = min(nums, key=lambda x: abs(x - correct_value))
        error = abs(closest - correct_value)
        error_rate = error / correct_value
        
        if error > tolerance:
            severity = "critical" if error_rate > 0.5 else "high" if error_rate > 0.1 else "medium"
            issues.append({
                "type": "numerical_deviation",
                "severity": severity,
                "description": f"数值偏差过大: {error:.0f} ({error_rate*100:.1f}%)",
                "closest_value": closest,
                "correct_value": correct_value,
                "error": error,
                "response_preview": response[:200]
            })
        
        # 检查数量级
        if closest / correct_value > 10 or correct_value / closest > 10:
            issues.append({
                "type": "magnitude_error",
                "severity": "critical",
                "description": "数量级错误（偏差超过10倍）",
                "closest_value": closest,
                "correct_value": correct_value,
                "response_preview": response[:200]
            })
        
        # 检查是否有多个矛盾的数值
        unique_nums = set(nums)
        if len(unique_nums) > 3:
            issues.append({
                "type": "contradictory_numbers",
                "severity": "medium",
                "description": f"包含多个不同数值({len(unique_nums)}个)，可能造成混淆",
                "numbers": list(unique_nums),
                "response_preview": response[:200]
            })
        
        return issues
    
    def diagnose_source_attribution(self, result):
        """诊断来源归属失败"""
        issues = []
        
        response = result.details.get('response', '')
        
        # 检查是否说明知识限制
        limitation_indicators = [
            "训练数据", "知识截止", "截至.*年", "无法获取最新",
            "建议查阅", "请参考", "权威来源"
        ]
        
        has_limitation = any(
            re.search(ind, response) 
            for ind in limitation_indicators
        )
        
        # 检查是否提供来源
        source_indicators = [
            "根据", "来源", "参考", "引用", "出处"
        ]
        
        has_source = any(ind in response for ind in source_indicators)
        
        # 检查是否可能编造来源
        fabricated_source_indicators = [
            r"20\d{2}年.*发表", r"《.*》.*论文", 
            r"Nature|Science|Cell", r"研究人员.*发现"
        ]
        
        possible_fabrication = any(
            re.search(ind, response) 
            for ind in fabricated_source_indicators
        )
        
        if not has_limitation and not has_source:
            issues.append({
                "type": "no_source_or_limitation",
                "severity": "high",
                "description": "既未说明知识限制，也未提供来源",
                "response_preview": response[:200]
            })
        
        if possible_fabrication and not has_limitation:
            issues.append({
                "type": "possible_fabricated_source",
                "severity": "critical",
                "description": "可能编造了研究来源，且未说明知识限制",
                "response_preview": response[:200]
            })
        
        return issues
    
    def diagnose_consistency(self, result):
        """诊断一致性失败"""
        issues = []
        
        response1 = result.details.get('response1', '')
        response2 = result.details.get('response2', '')
        
        # 简单的相似度检查
        similarity = self.calculate_similarity(response1, response2)
        
        if similarity < 0.5:
            issues.append({
                "type": "low_consistency",
                "severity": "high",
                "description": f"两次回答相似度过低: {similarity*100:.1f}%",
                "similarity": similarity,
                "response1_preview": response1[:150],
                "response2_preview": response2[:150]
            })
        
        # 检查关键信息是否一致
        key_info1 = self.extract_key_info(response1)
        key_info2 = self.extract_key_info(response2)
        
        if key_info1 != key_info2:
            issues.append({
                "type": "contradictory_key_info",
                "severity": "critical",
                "description": "关键信息不一致",
                "key_info1": key_info1,
                "key_info2": key_info2
            })
        
        return issues
    
    def calculate_similarity(self, text1, text2):
        """计算文本相似度（简单实现）"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def extract_key_info(self, text):
        """提取关键信息（年份、数字等）"""
        # 提取年份
        years = re.findall(r'19\d{2}|20\d{2}', text)
        # 提取数字
        numbers = re.findall(r'\d+', text)
        
        return {
            "years": years,
            "numbers": numbers
        }
    
    def generate_recommendations(self, all_issues):
        """生成修复建议"""
        recommendations = []
        
        # 统计问题类型
        issue_types = {}
        for issues in all_issues.values():
            for issue in issues:
                issue_type = issue['type']
                severity = issue['severity']
                
                if issue_type not in issue_types:
                    issue_types[issue_type] = {"count": 0, "max_severity": "low"}
                
                issue_types[issue_type]["count"] += 1
                
                # 更新最高严重级别
                severity_order = ["low", "medium", "high", "critical"]
                if severity_order.index(severity) > severity_order.index(issue_types[issue_type]["max_severity"]):
                    issue_types[issue_type]["max_severity"] = severity
        
        # 根据问题类型生成建议
        if "factual_error" in issue_types or "missing_correct_answer" in issue_types:
            recommendations.append({
                "priority": "high",
                "category": "事实准确性",
                "actions": [
                    "优化系统提示词，强调事实准确性",
                    "降低temperature参数到0.1-0.3",
                    "添加事实验证层，使用知识库验证答案",
                    "对基本常识问题使用预定义答案"
                ]
            })
        
        if "fabrication" in issue_types or "lack_of_honesty" in issue_types:
            recommendations.append({
                "priority": "critical",
                "category": "诚实性",
                "actions": [
                    "强化系统提示词，要求承认不知道",
                    "添加概念验证机制",
                    "实现置信度评估",
                    "对虚构概念返回标准回复"
                ]
            })
        
        if "numerical_deviation" in issue_types or "magnitude_error" in issue_types:
            recommendations.append({
                "priority": "high",
                "category": "数值准确性",
                "actions": [
                    "建立数值知识库",
                    "添加数值验证机制",
                    "使用更低的temperature参数",
                    "对数值问题添加单位和精度说明"
                ]
            })
        
        if "no_source_or_limitation" in issue_types or "possible_fabricated_source" in issue_types:
            recommendations.append({
                "priority": "high",
                "category": "来源归属",
                "actions": [
                    "在系统提示词中明确知识截止日期",
                    "要求对最新信息说明无法获取",
                    "禁止编造论文和研究引用",
                    "建议用户查阅权威来源"
                ]
            })
        
        if "low_consistency" in issue_types or "contradictory_key_info" in issue_types:
            recommendations.append({
                "priority": "medium",
                "category": "一致性",
                "actions": [
                    "降低temperature参数",
                    "使用固定的随机种子",
                    "对相同问题使用缓存",
                    "添加一致性验证机制"
                ]
            })
        
        return recommendations
    
    def run_diagnosis(self, base_url=None):
        """运行完整诊断"""
        print("="*70)
        print("幻觉测试诊断工具")
        print("="*70)
        
        url = base_url or BASE_URL
        print(f"\n测试URL: {url}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 运行幻觉测试
        print("正在运行幻觉检测测试...")
        tester = HallucinationTest(url)
        
        tester.test_factual_accuracy()
        tester.test_unknown_knowledge()
        tester.test_numerical_accuracy()
        tester.test_source_attribution()
        tester.test_consistency()
        
        # 诊断每个测试结果
        all_issues = {}
        
        for result in tester.results:
            print(f"\n{'='*70}")
            print(f"测试: {result.name}")
            print(f"状态: {'✓ 通过' if result.passed else '✗ 失败'}")
            print(f"得分: {result.score:.1f}/100")
            print(f"耗时: {result.duration:.2f}s")
            
            if not result.passed:
                # 根据测试类型进行诊断
                if "事实准确性" in result.name:
                    issues = self.diagnose_factual_accuracy(result)
                elif "未知知识" in result.name:
                    issues = self.diagnose_unknown_knowledge(result)
                elif "数值准确性" in result.name:
                    issues = self.diagnose_numerical_accuracy(result)
                elif "来源归属" in result.name:
                    issues = self.diagnose_source_attribution(result)
                elif "一致性" in result.name:
                    issues = self.diagnose_consistency(result)
                else:
                    issues = []
                
                all_issues[result.name] = issues
                
                if issues:
                    print(f"\n发现 {len(issues)} 个问题:")
                    for i, issue in enumerate(issues, 1):
                        severity_label = self.severity_levels.get(issue['severity'], issue['severity'])
                        print(f"\n  {i}. [{severity_label}] {issue['description']}")
                        if 'response_preview' in issue:
                            print(f"     响应预览: {issue['response_preview'][:100]}...")
        
        # 生成建议
        print(f"\n{'='*70}")
        print("修复建议")
        print("="*70)
        
        recommendations = self.generate_recommendations(all_issues)
        
        if recommendations:
            for rec in recommendations:
                priority_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }
                emoji = priority_emoji.get(rec['priority'], "")
                
                print(f"\n{emoji} {rec['category']} (优先级: {rec['priority']})")
                for action in rec['actions']:
                    print(f"  • {action}")
        else:
            print("\n✅ 所有测试通过，无需修复！")
        
        # 生成诊断报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "total_tests": len(tester.results),
            "passed_tests": sum(1 for r in tester.results if r.passed),
            "failed_tests": sum(1 for r in tester.results if not r.passed),
            "average_score": sum(r.score for r in tester.results) / len(tester.results),
            "issues": all_issues,
            "recommendations": recommendations
        }
        
        # 保存报告
        report_file = f"hallucination_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*70}")
        print(f"诊断报告已保存到: {report_file}")
        print("="*70)
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='幻觉测试诊断工具')
    parser.add_argument(
        '--url',
        default=BASE_URL,
        help='智能体API地址 (默认: http://10.225.8.186/api/v1)'
    )
    
    args = parser.parse_args()
    
    diagnostic = HallucinationDiagnostic()
    diagnostic.run_diagnosis(args.url)


if __name__ == "__main__":
    main()

