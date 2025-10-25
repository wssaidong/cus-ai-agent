"""
智能体成熟度验证测试脚本

测试维度：
1. 基础能力 - 健康检查、基本对话
2. 工具调用 - 单工具、多工具、工具链
3. 推理能力 - 逻辑推理、上下文理解、多轮对话
4. 错误处理 - 异常输入、边界条件、容错能力
5. 性能指标 - 响应时间、并发处理、资源使用
6. OpenAI兼容性 - API兼容性、流式输出
7. 幻觉检测 - 事实准确性、未知知识处理、数值准确性、来源归属、一致性
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import concurrent.futures


# ==================== 配置 ====================

# 智能体API地址
BASE_URL = "http://10.225.8.186/api/v1"

# 测试超时时间（秒）
TIMEOUT = 60

# 并发测试数量
CONCURRENT_REQUESTS = 5


# ==================== 数据模型 ====================

@dataclass
class TestResult:
    """测试结果"""
    name: str
    category: str
    passed: bool
    score: float  # 0-100
    duration: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class MaturityReport:
    """成熟度报告"""
    total_score: float
    category_scores: Dict[str, float]
    test_results: List[TestResult]
    summary: Dict[str, Any]
    timestamp: str


# ==================== 测试基类 ====================

class AgentMaturityTest:
    """智能体成熟度测试基类"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: List[TestResult] = []

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict] = None,
        timeout: int = TIMEOUT
    ) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            return requests.get(url, timeout=timeout)
        elif method == "POST":
            return requests.post(url, json=data, timeout=timeout)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")

    def _record_result(
        self,
        name: str,
        category: str,
        passed: bool,
        score: float,
        duration: float,
        message: str,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """记录测试结果"""
        result = TestResult(
            name=name,
            category=category,
            passed=passed,
            score=score,
            duration=duration,
            message=message,
            details=details or {},
            error=error
        )
        self.results.append(result)

        # 打印结果
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {message} (得分: {score:.1f}/100, 耗时: {duration:.2f}s)")
        if error:
            print(f"  错误: {error}")


# ==================== 1. 基础能力测试 ====================

class BasicCapabilityTest(AgentMaturityTest):
    """基础能力测试"""

    def test_health_check(self):
        """测试健康检查"""
        print("\n[基础能力] 测试健康检查...")
        start = time.time()

        try:
            response = self._make_request("/health", method="GET", timeout=5)
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                passed = "status" in data and data["status"] == "healthy"
                score = 100 if passed else 50
                message = "服务健康" if passed else "服务状态异常"
                self._record_result(
                    "健康检查", "基础能力", passed, score, duration, message,
                    details=data
                )
            else:
                self._record_result(
                    "健康检查", "基础能力", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "健康检查", "基础能力", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_basic_chat(self):
        """测试基本对话"""
        print("\n[基础能力] 测试基本对话...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "你好，请简单介绍一下你自己"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 评分标准
                score = 0
                if content:
                    score += 50  # 有响应
                    if len(content) > 20:
                        score += 25  # 响应足够长
                    if any(word in content for word in ["智能", "助手", "帮助", "AI"]):
                        score += 25  # 响应相关

                passed = score >= 75
                self._record_result(
                    "基本对话", "基础能力", passed, score, duration,
                    f"响应长度: {len(content)}字符",
                    details={"response": content[:100]}
                )
            else:
                self._record_result(
                    "基本对话", "基础能力", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "基本对话", "基础能力", False, 0, duration,
                "请求失败", error=str(e)
            )


# ==================== 2. 工具调用测试 ====================

class ToolCallingTest(AgentMaturityTest):
    """工具调用测试"""

    def test_calculator_tool(self):
        """测试计算器工具"""
        print("\n[工具调用] 测试计算器工具...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "帮我计算 123 * 456 的结果"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 正确答案是 56088
                correct_answer = "56088"
                score = 0

                if content:
                    score += 40  # 有响应
                    if correct_answer in content or "56,088" in content:
                        score += 60  # 答案正确

                passed = score >= 80
                self._record_result(
                    "计算器工具", "工具调用", passed, score, duration,
                    f"答案{'正确' if passed else '错误'}",
                    details={"response": content}
                )
            else:
                self._record_result(
                    "计算器工具", "工具调用", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "计算器工具", "工具调用", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_string_tool(self):
        """测试字符串处理工具"""
        print("\n[工具调用] 测试字符串处理工具...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "请把 'hello world' 转换成大写"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                score = 0
                if content:
                    score += 40
                    if "HELLO WORLD" in content:
                        score += 60

                passed = score >= 80
                self._record_result(
                    "字符串工具", "工具调用", passed, score, duration,
                    f"转换{'成功' if passed else '失败'}",
                    details={"response": content}
                )
            else:
                self._record_result(
                    "字符串工具", "工具调用", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "字符串工具", "工具调用", False, 0, duration,
                "请求失败", error=str(e)
            )


# ==================== 3. 推理能力测试 ====================

class ReasoningTest(AgentMaturityTest):
    """推理能力测试"""

    def test_logical_reasoning(self):
        """测试逻辑推理"""
        print("\n[推理能力] 测试逻辑推理...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "如果所有的猫都是动物，而Tom是一只猫，那么Tom是什么？"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                score = 0
                if content:
                    score += 40
                    if "动物" in content:
                        score += 60

                passed = score >= 80
                self._record_result(
                    "逻辑推理", "推理能力", passed, score, duration,
                    f"推理{'正确' if passed else '错误'}",
                    details={"response": content}
                )
            else:
                self._record_result(
                    "逻辑推理", "推理能力", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "逻辑推理", "推理能力", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_multi_turn_conversation(self):
        """测试多轮对话"""
        print("\n[推理能力] 测试多轮对话...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "我有10个苹果"},
                        {"role": "assistant", "content": "好的，你有10个苹果。"},
                        {"role": "user", "content": "我吃了3个，还剩多少？"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                score = 0
                if content:
                    score += 40
                    if "7" in content:
                        score += 60

                passed = score >= 80
                self._record_result(
                    "多轮对话", "推理能力", passed, score, duration,
                    f"上下文理解{'正确' if passed else '错误'}",
                    details={"response": content}
                )
            else:
                self._record_result(
                    "多轮对话", "推理能力", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "多轮对话", "推理能力", False, 0, duration,
                "请求失败", error=str(e)
            )


# ==================== 4. 错误处理测试 ====================

class ErrorHandlingTest(AgentMaturityTest):
    """错误处理测试"""

    def test_empty_message(self):
        """测试空消息处理"""
        print("\n[错误处理] 测试空消息处理...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": []
                }
            )
            duration = time.time() - start

            # 应该返回422错误
            passed = response.status_code == 422
            score = 100 if passed else 0

            self._record_result(
                "空消息处理", "错误处理", passed, score, duration,
                f"正确返回422错误" if passed else f"状态码: {response.status_code}"
            )
        except Exception as e:
            duration = time.time() - start
            # 抛出异常也算正确处理
            self._record_result(
                "空消息处理", "错误处理", True, 100, duration,
                "正确抛出异常", details={"error": str(e)}
            )

    def test_invalid_parameters(self):
        """测试无效参数处理"""
        print("\n[错误处理] 测试无效参数处理...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [{"role": "user", "content": "测试"}],
                    "temperature": 5.0  # 超出范围
                }
            )
            duration = time.time() - start

            # 应该返回422错误
            passed = response.status_code == 422
            score = 100 if passed else 0

            self._record_result(
                "无效参数处理", "错误处理", passed, score, duration,
                f"正确返回422错误" if passed else f"状态码: {response.status_code}"
            )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "无效参数处理", "错误处理", True, 100, duration,
                "正确抛出异常", details={"error": str(e)}
            )


# ==================== 5. 性能测试 ====================

class PerformanceTest(AgentMaturityTest):
    """性能测试"""

    def test_response_time(self):
        """测试响应时间"""
        print("\n[性能测试] 测试响应时间...")

        times = []
        for i in range(3):
            start = time.time()
            try:
                response = self._make_request(
                    "/chat/completions",
                    data={
                        "model": "gpt-4-turbo-preview",
                        "messages": [{"role": "user", "content": "你好"}]
                    }
                )
                duration = time.time() - start

                if response.status_code == 200:
                    times.append(duration)
                    print(f"  第{i+1}次请求: {duration:.2f}s")
            except Exception as e:
                print(f"  第{i+1}次请求失败: {str(e)}")

        if times:
            avg_time = sum(times) / len(times)

            # 评分标准：<3s=100, <5s=80, <10s=60, <15s=40, >=15s=20
            if avg_time < 3:
                score = 100
            elif avg_time < 5:
                score = 80
            elif avg_time < 10:
                score = 60
            elif avg_time < 15:
                score = 40
            else:
                score = 20

            passed = score >= 60
            self._record_result(
                "响应时间", "性能测试", passed, score, avg_time,
                f"平均响应时间: {avg_time:.2f}s",
                details={"times": times, "avg": avg_time}
            )
        else:
            self._record_result(
                "响应时间", "性能测试", False, 0, 0,
                "所有请求都失败"
            )

    def test_concurrent_requests(self):
        """测试并发处理"""
        print("\n[性能测试] 测试并发处理...")
        start = time.time()

        def make_single_request(index):
            try:
                response = self._make_request(
                    "/chat/completions",
                    data={
                        "model": "gpt-4-turbo-preview",
                        "messages": [{"role": "user", "content": f"测试{index}"}]
                    }
                )
                return response.status_code == 200
            except:
                return False

        # 并发5个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            futures = [executor.submit(make_single_request, i) for i in range(CONCURRENT_REQUESTS)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start
        success_count = sum(results)

        # 评分标准：全部成功=100, 80%成功=80, 60%成功=60
        score = (success_count / CONCURRENT_REQUESTS) * 100
        passed = score >= 80

        self._record_result(
            "并发处理", "性能测试", passed, score, duration,
            f"成功: {success_count}/{CONCURRENT_REQUESTS}",
            details={"success_count": success_count, "total": CONCURRENT_REQUESTS}
        )


# ==================== 6. OpenAI兼容性测试 ====================

class OpenAICompatibilityTest(AgentMaturityTest):
    """OpenAI兼容性测试"""

    def test_streaming_response(self):
        """测试流式响应"""
        print("\n[OpenAI兼容] 测试流式响应...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [{"role": "user", "content": "数到5"}],
                    "stream": True
                }
            )

            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk:
                                chunk_count += 1
                        except json.JSONDecodeError:
                            pass

            duration = time.time() - start

            # 评分标准
            score = 0
            if chunk_count > 0:
                score += 60  # 有流式输出
                if chunk_count >= 3:
                    score += 40  # 输出足够多

            passed = score >= 80
            self._record_result(
                "流式响应", "OpenAI兼容", passed, score, duration,
                f"接收到{chunk_count}个数据块",
                details={"chunk_count": chunk_count}
            )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "流式响应", "OpenAI兼容", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_response_format(self):
        """测试响应格式"""
        print("\n[OpenAI兼容] 测试响应格式...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [{"role": "user", "content": "测试"}]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()

                # 检查必需字段
                required_fields = ["id", "object", "created", "model", "choices", "usage"]
                score = 0

                for field in required_fields:
                    if field in data:
                        score += 100 / len(required_fields)

                passed = score >= 90
                self._record_result(
                    "响应格式", "OpenAI兼容", passed, score, duration,
                    f"包含{sum(1 for f in required_fields if f in data)}/{len(required_fields)}个必需字段",
                    details={"fields": list(data.keys())}
                )
            else:
                self._record_result(
                    "响应格式", "OpenAI兼容", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "响应格式", "OpenAI兼容", False, 0, duration,
                "请求失败", error=str(e)
            )


# ==================== 7. 幻觉检测测试 ====================

class HallucinationTest(AgentMaturityTest):
    """幻觉检测测试"""

    def test_factual_accuracy(self):
        """测试事实准确性"""
        print("\n[幻觉检测] 测试事实准确性...")
        start = time.time()

        try:
            # 测试明确的事实性问题
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "地球有几个月亮？"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 评分标准
                score = 0
                if content:
                    score += 40  # 有响应

                    # 检查是否包含正确答案（1个月亮）
                    correct_indicators = ["1", "一个", "一颗", "唯一"]
                    wrong_indicators = ["2", "3", "多个", "几个", "两个", "三个"]

                    has_correct = any(ind in content for ind in correct_indicators)
                    has_wrong = any(ind in content for ind in wrong_indicators)

                    if has_correct and not has_wrong:
                        score += 60  # 答案正确
                    elif has_correct and has_wrong:
                        score += 30  # 答案模糊
                    elif has_wrong:
                        score = 0  # 明显错误（幻觉）

                passed = score >= 80
                hallucination = score < 40

                self._record_result(
                    "事实准确性", "幻觉检测", passed, score, duration,
                    f"{'存在幻觉' if hallucination else '事实准确' if passed else '答案模糊'}",
                    details={
                        "response": content,
                        "hallucination_detected": hallucination
                    }
                )
            else:
                self._record_result(
                    "事实准确性", "幻觉检测", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "事实准确性", "幻觉检测", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_unknown_knowledge(self):
        """测试对未知知识的处理"""
        print("\n[幻觉检测] 测试未知知识处理...")
        start = time.time()

        try:
            # 询问一个不存在的概念
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "请介绍一下量子纠缠反转器的工作原理"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 评分标准：应该承认不知道或说明这不是真实的概念
                score = 0
                if content:
                    score += 30  # 有响应

                    # 检查是否承认不确定或不存在
                    honest_indicators = [
                        "不确定", "不清楚", "不了解", "没有听说",
                        "不存在", "虚构", "不是真实", "无法确认",
                        "可能不", "似乎不", "据我所知没有"
                    ]

                    # 检查是否编造了详细解释（幻觉）
                    fabrication_indicators = [
                        "工作原理是", "主要由", "通过", "利用",
                        "首先", "然后", "最后", "步骤"
                    ]

                    has_honest = any(ind in content for ind in honest_indicators)
                    has_fabrication = sum(1 for ind in fabrication_indicators if ind in content) >= 3

                    if has_honest and not has_fabrication:
                        score += 70  # 诚实承认不知道
                    elif has_honest and has_fabrication:
                        score += 30  # 部分承认但也有编造
                    elif has_fabrication:
                        score = 0  # 明显编造（严重幻觉）
                    else:
                        score += 50  # 谨慎回答

                passed = score >= 70
                hallucination = score < 30

                self._record_result(
                    "未知知识处理", "幻觉检测", passed, score, duration,
                    f"{'严重幻觉' if hallucination else '诚实回答' if passed else '部分编造'}",
                    details={
                        "response": content[:200],
                        "hallucination_detected": hallucination
                    }
                )
            else:
                self._record_result(
                    "未知知识处理", "幻觉检测", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "未知知识处理", "幻觉检测", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_numerical_accuracy(self):
        """测试数值准确性"""
        print("\n[幻觉检测] 测试数值准确性...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "珠穆朗玛峰的海拔高度是多少米？"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 正确答案约为8848米或8849米
                score = 0
                if content:
                    score += 40  # 有响应

                    # 检查数值范围（允许一定误差）
                    import re
                    numbers = re.findall(r'\d+', content)

                    correct_range = False
                    for num_str in numbers:
                        num = int(num_str)
                        # 8800-8900米之间认为正确
                        if 8800 <= num <= 8900:
                            correct_range = True
                            break

                    if correct_range:
                        score += 60  # 数值准确
                    elif numbers:
                        # 检查是否严重偏离
                        max_num = max(int(n) for n in numbers if len(n) >= 4)
                        if max_num < 7000 or max_num > 10000:
                            score = 0  # 严重错误（幻觉）
                        else:
                            score += 30  # 数值接近但不准确

                passed = score >= 80
                hallucination = score == 0

                self._record_result(
                    "数值准确性", "幻觉检测", passed, score, duration,
                    f"{'数值幻觉' if hallucination else '数值准确' if passed else '数值偏差'}",
                    details={
                        "response": content,
                        "hallucination_detected": hallucination
                    }
                )
            else:
                self._record_result(
                    "数值准确性", "幻觉检测", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "数值准确性", "幻觉检测", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_source_attribution(self):
        """测试来源归属"""
        print("\n[幻觉检测] 测试来源归属...")
        start = time.time()

        try:
            response = self._make_request(
                "/chat/completions",
                data={
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "user", "content": "请告诉我一个关于人工智能的最新研究成果，并说明来源"}
                    ]
                }
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                score = 0
                if content:
                    score += 40  # 有响应

                    # 检查是否提供了来源或承认限制
                    source_indicators = [
                        "根据", "来自", "发表于", "论文", "研究",
                        "报告", "期刊", "会议", "作者"
                    ]

                    limitation_indicators = [
                        "截至", "训练数据", "知识截止", "无法获取最新",
                        "不能确认", "建议查阅", "可能需要"
                    ]

                    has_source = any(ind in content for ind in source_indicators)
                    has_limitation = any(ind in content for ind in limitation_indicators)

                    if has_limitation:
                        score += 60  # 诚实说明限制
                    elif has_source:
                        score += 40  # 提供了来源（但可能不准确）
                    else:
                        score += 10  # 没有来源说明

                passed = score >= 70

                self._record_result(
                    "来源归属", "幻觉检测", passed, score, duration,
                    f"{'说明限制' if score >= 90 else '提供来源' if score >= 70 else '缺少来源'}",
                    details={"response": content[:200]}
                )
            else:
                self._record_result(
                    "来源归属", "幻觉检测", False, 0, duration,
                    f"HTTP状态码错误: {response.status_code}"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "来源归属", "幻觉检测", False, 0, duration,
                "请求失败", error=str(e)
            )

    def test_consistency(self):
        """测试一致性"""
        print("\n[幻觉检测] 测试回答一致性...")
        start = time.time()

        try:
            # 同一个问题问两次
            question = "Python是什么时候发布的？"

            responses = []
            for i in range(2):
                response = self._make_request(
                    "/chat/completions",
                    data={
                        "model": "gpt-4-turbo-preview",
                        "messages": [
                            {"role": "user", "content": question}
                        ],
                        "temperature": 0.3  # 低温度以减少随机性
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    responses.append(content)

                time.sleep(0.5)  # 短暂延迟

            duration = time.time() - start

            if len(responses) == 2:
                # 检查两次回答的一致性
                import re

                # 提取年份
                years1 = set(re.findall(r'19\d{2}|20\d{2}', responses[0]))
                years2 = set(re.findall(r'19\d{2}|20\d{2}', responses[1]))

                score = 0
                score += 40  # 有响应

                # 检查年份是否一致
                if years1 and years2:
                    if years1 == years2:
                        score += 60  # 完全一致
                    elif years1 & years2:  # 有交集
                        score += 30  # 部分一致
                    else:
                        score = 20  # 不一致（可能幻觉）
                else:
                    score += 30  # 没有具体年份

                passed = score >= 80
                inconsistent = score < 50

                self._record_result(
                    "回答一致性", "幻觉检测", passed, score, duration,
                    f"{'不一致' if inconsistent else '一致' if passed else '部分一致'}",
                    details={
                        "response1": responses[0][:100],
                        "response2": responses[1][:100],
                        "years1": list(years1),
                        "years2": list(years2),
                        "inconsistent": inconsistent
                    }
                )
            else:
                self._record_result(
                    "回答一致性", "幻觉检测", False, 0, duration,
                    "无法获取两次响应"
                )
        except Exception as e:
            duration = time.time() - start
            self._record_result(
                "回答一致性", "幻觉检测", False, 0, duration,
                "请求失败", error=str(e)
            )


# ==================== 测试运行器 ====================

class MaturityTestRunner:
    """成熟度测试运行器"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.all_results: List[TestResult] = []

    def run_all_tests(self) -> MaturityReport:
        """运行所有测试"""
        print("\n" + "="*70)
        print("智能体成熟度验证测试")
        print("="*70)
        print(f"测试地址: {self.base_url}")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        # 检查服务是否可用
        if not self._check_service():
            print("\n✗ 服务不可用，测试终止")
            return self._generate_report()

        print("\n✓ 服务可用，开始测试...\n")

        # 运行各类测试
        test_classes = [
            BasicCapabilityTest,
            ToolCallingTest,
            ReasoningTest,
            ErrorHandlingTest,
            PerformanceTest,
            OpenAICompatibilityTest,
            HallucinationTest,  # 幻觉检测测试
        ]

        for test_class in test_classes:
            try:
                tester = test_class(self.base_url)

                # 运行该类的所有测试方法
                for method_name in dir(tester):
                    if method_name.startswith('test_'):
                        method = getattr(tester, method_name)
                        if callable(method):
                            try:
                                method()
                            except Exception as e:
                                print(f"✗ {method_name} 执行失败: {str(e)}")

                # 收集结果
                self.all_results.extend(tester.results)
            except Exception as e:
                print(f"✗ {test_class.__name__} 初始化失败: {str(e)}")

        # 生成报告
        return self._generate_report()

    def _check_service(self) -> bool:
        """检查服务是否可用"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _generate_report(self) -> MaturityReport:
        """生成成熟度报告"""
        if not self.all_results:
            return MaturityReport(
                total_score=0,
                category_scores={},
                test_results=[],
                summary={"message": "没有测试结果"},
                timestamp=datetime.now().isoformat()
            )

        # 按类别统计
        category_scores = {}
        category_counts = {}

        for result in self.all_results:
            if result.category not in category_scores:
                category_scores[result.category] = 0
                category_counts[result.category] = 0

            category_scores[result.category] += result.score
            category_counts[result.category] += 1

        # 计算平均分
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] /= category_counts[category]

        # 计算总分
        total_score = sum(category_scores.values()) / len(category_scores) if category_scores else 0

        # 统计信息
        passed_count = sum(1 for r in self.all_results if r.passed)
        total_count = len(self.all_results)
        avg_duration = sum(r.duration for r in self.all_results) / total_count if total_count > 0 else 0

        summary = {
            "total_tests": total_count,
            "passed_tests": passed_count,
            "failed_tests": total_count - passed_count,
            "pass_rate": f"{(passed_count/total_count*100):.1f}%" if total_count > 0 else "0%",
            "avg_duration": f"{avg_duration:.2f}s",
            "maturity_level": self._get_maturity_level(total_score)
        }

        return MaturityReport(
            total_score=total_score,
            category_scores=category_scores,
            test_results=self.all_results,
            summary=summary,
            timestamp=datetime.now().isoformat()
        )

    def _get_maturity_level(self, score: float) -> str:
        """根据分数获取成熟度等级"""
        if score >= 90:
            return "优秀 (Excellent)"
        elif score >= 80:
            return "良好 (Good)"
        elif score >= 70:
            return "中等 (Fair)"
        elif score >= 60:
            return "及格 (Pass)"
        else:
            return "不及格 (Fail)"

    def print_report(self, report: MaturityReport):
        """打印报告"""
        print("\n" + "="*70)
        print("测试报告")
        print("="*70)

        # 总体评分
        print(f"\n【总体评分】")
        print(f"  总分: {report.total_score:.1f}/100")
        print(f"  成熟度等级: {report.summary['maturity_level']}")
        print(f"  通过率: {report.summary['pass_rate']}")
        print(f"  平均响应时间: {report.summary['avg_duration']}")

        # 分类评分
        print(f"\n【分类评分】")
        for category, score in sorted(report.category_scores.items()):
            bar_length = int(score / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"  {category:12s}: {score:5.1f}/100 {bar}")

        # 测试详情
        print(f"\n【测试详情】")
        print(f"  总测试数: {report.summary['total_tests']}")
        print(f"  通过: {report.summary['passed_tests']}")
        print(f"  失败: {report.summary['failed_tests']}")

        # 失败的测试
        failed_tests = [r for r in report.test_results if not r.passed]
        if failed_tests:
            print(f"\n【失败的测试】")
            for result in failed_tests:
                print(f"  ✗ {result.name} ({result.category})")
                print(f"    原因: {result.message}")
                if result.error:
                    print(f"    错误: {result.error}")

        print("\n" + "="*70)

    def save_report(self, report: MaturityReport, filename: str = "maturity_report.json"):
        """保存报告到文件"""
        report_dict = {
            "total_score": report.total_score,
            "category_scores": report.category_scores,
            "summary": report.summary,
            "timestamp": report.timestamp,
            "test_results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "score": r.score,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details,
                    "error": r.error
                }
                for r in report.test_results
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存到: {filename}")


# ==================== 主函数 ====================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='智能体成熟度验证测试')
    parser.add_argument('--url', default=BASE_URL, help='智能体API地址')
    parser.add_argument('--output', default='maturity_report.json', help='报告输出文件')
    args = parser.parse_args()

    # 运行测试
    runner = MaturityTestRunner(base_url=args.url)
    report = runner.run_all_tests()

    # 打印报告
    runner.print_report(report)

    # 保存报告
    runner.save_report(report, args.output)

    # 返回退出码
    return 0 if report.total_score >= 60 else 1


if __name__ == "__main__":
    exit(main())
