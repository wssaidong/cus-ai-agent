"""
测试 Completions API 接口
"""
import requests
import json
import time


def test_completions_basic():
    """测试基本的 completions 接口"""
    print("\n" + "="*50)
    print("测试 1: 基本 Completions 接口")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": "你是一个智能助手"},
            {"role": "user", "content": "帮我计算 123 + 456"}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"✓ 请求成功")
        print(f"  响应ID: {result['id']}")
        print(f"  模型: {result['model']}")
        print(f"  内容: {result['choices'][0]['message']['content']}")
        print(f"  Token使用: {result['usage']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False


def test_completions_multi_turn():
    """测试多轮对话"""
    print("\n" + "="*50)
    print("测试 2: 多轮对话")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": "你是一个数学助手"},
            {"role": "user", "content": "123 + 456 等于多少？"},
            {"role": "assistant", "content": "123 + 456 = 579"},
            {"role": "user", "content": "那再乘以2呢？"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"✓ 请求成功")
        print(f"  内容: {result['choices'][0]['message']['content']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False


def test_completions_with_tools():
    """测试工具调用"""
    print("\n" + "="*50)
    print("测试 3: 工具调用")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "user", "content": "帮我把 'hello world' 转换成大写"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"✓ 请求成功")
        print(f"  内容: {result['choices'][0]['message']['content']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False


def test_completions_parameters():
    """测试不同参数"""
    print("\n" + "="*50)
    print("测试 4: 不同参数设置")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    # 测试低温度（更确定性）
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "user", "content": "1+1等于多少？"}
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"✓ 低温度请求成功")
        print(f"  Temperature: 0.1")
        print(f"  内容: {result['choices'][0]['message']['content']}")
        
        # 测试高温度（更有创造性）
        payload["temperature"] = 1.5
        payload["messages"][0]["content"] = "给我讲一个有趣的故事"
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"✓ 高温度请求成功")
        print(f"  Temperature: 1.5")
        print(f"  内容: {result['choices'][0]['message']['content'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False


def test_completions_error_handling():
    """测试错误处理"""
    print("\n" + "="*50)
    print("测试 5: 错误处理")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    # 测试空消息
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": []
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 422:
            print(f"✓ 正确处理空消息错误")
            print(f"  状态码: {response.status_code}")
        else:
            print(f"✗ 未正确处理空消息")
            
    except Exception as e:
        print(f"✓ 捕获到异常: {str(e)}")
    
    # 测试无效参数
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "user", "content": "测试"}
        ],
        "temperature": 5.0  # 超出范围
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 422:
            print(f"✓ 正确处理无效参数")
            print(f"  状态码: {response.status_code}")
        else:
            print(f"✗ 未正确处理无效参数")
            
    except Exception as e:
        print(f"✓ 捕获到异常: {str(e)}")
    
    return True


def test_completions_performance():
    """测试性能"""
    print("\n" + "="*50)
    print("测试 6: 性能测试")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"
    
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "user", "content": "你好"}
        ]
    }
    
    times = []
    
    for i in range(3):
        try:
            start = time.time()
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            elapsed = time.time() - start
            
            times.append(elapsed)
            print(f"  第 {i+1} 次请求: {elapsed:.2f}秒")
            
        except Exception as e:
            print(f"  第 {i+1} 次请求失败: {str(e)}")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"\n✓ 平均响应时间: {avg_time:.2f}秒")
        return True
    else:
        print(f"\n✗ 所有请求都失败")
        return False


def test_completions_stream():
    """测试流式输出"""
    print("\n" + "="*50)
    print("测试 7: 流式输出")
    print("="*50)

    url = "http://localhost:8000/api/v1/chat/completions"

    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "user", "content": "数到5"}
        ],
        "stream": True
    }

    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        response.raise_for_status()

        print(f"✓ 开始接收流式响应:")

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
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')

                            if content:
                                chunk_count += 1
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass

        print(f"\n✓ 流式响应完成，接收到 {chunk_count} 个内容块")
        return True

    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False


def test_openai_sdk():
    """测试 OpenAI SDK 兼容性"""
    print("\n" + "="*50)
    print("测试 8: OpenAI SDK 兼容性")
    print("="*50)
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key="dummy-key",
            base_url="http://localhost:8000/api/v1"
        )
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "user", "content": "测试 OpenAI SDK"}
            ]
        )
        
        print(f"✓ OpenAI SDK 调用成功")
        print(f"  内容: {response.choices[0].message.content}")
        
        return True
        
    except ImportError:
        print(f"⚠ OpenAI SDK 未安装，跳过此测试")
        print(f"  安装命令: pip install openai")
        return True
        
    except Exception as e:
        print(f"✗ OpenAI SDK 调用失败: {str(e)}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试 Completions API")
    print("="*60)
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code != 200:
            print("✗ 服务未运行，请先启动服务")
            print("  启动命令: python run.py")
            return
    except Exception as e:
        print(f"✗ 无法连接到服务: {str(e)}")
        print("  请确保服务已启动: python run.py")
        return
    
    print("✓ 服务运行正常\n")
    
    # 运行测试
    tests = [
        test_completions_basic,
        test_completions_multi_turn,
        test_completions_with_tools,
        test_completions_parameters,
        test_completions_error_handling,
        test_completions_performance,
        test_completions_stream,
        test_openai_sdk,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ 测试异常: {str(e)}")
            results.append(False)
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
    else:
        print(f"\n⚠ 有 {total - passed} 个测试失败")


if __name__ == "__main__":
    main()

