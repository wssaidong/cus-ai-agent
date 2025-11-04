"""
多智能体系统使用示例

演示如何使用多智能体系统完成各种任务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.multi_agent.multi_agent_state import create_initial_state
from src.agent.multi_agent.multi_agent_graph import multi_agent_graph
from src.agent.multi_agent.agent_registry import agent_registry
from src.utils import app_logger


async def example_1_sequential_mode():
    """
    示例 1: 顺序协作模式
    
    场景: 产品需求分析和规划
    """
    print("\n" + "=" * 60)
    print("示例 1: 顺序协作模式 - 产品需求分析")
    print("=" * 60)
    
    # 定义任务
    task = {
        "description": "分析并制定移动支付功能的开发计划",
        "type": "product_planning",
        "context": "公司准备开发移动支付功能,需要完整的需求分析和开发计划",
        "requirements": [
            "用户需求分析",
            "功能模块设计",
            "开发时间估算",
            "风险评估"
        ]
    }
    
    # 创建初始状态
    initial_state = create_initial_state(
        task=task,
        coordination_mode="sequential",
        max_iterations=10
    )
    
    # 执行任务
    print("\n开始执行任务...")
    result = await multi_agent_graph.ainvoke(initial_state)
    
    # 输出结果
    print("\n执行结果:")
    print(f"- 是否完成: {result.get('is_finished')}")
    print(f"- 参与智能体: {list(result.get('agent_results', {}).keys())}")
    print(f"- 最终结果: {result.get('final_result', {}).get('summary', 'N/A')}")
    
    return result


async def example_2_feedback_mode():
    """
    示例 2: 反馈协作模式
    
    场景: 代码生成与优化
    """
    print("\n" + "=" * 60)
    print("示例 2: 反馈协作模式 - 代码生成与优化")
    print("=" * 60)
    
    # 定义任务
    task = {
        "description": "生成一个高质量的快速排序算法实现",
        "type": "code_generation",
        "requirements": [
            "使用 Python 实现",
            "时间复杂度 O(n log n)",
            "包含详细注释",
            "包含单元测试",
            "代码风格符合 PEP 8"
        ]
    }
    
    # 创建初始状态
    initial_state = create_initial_state(
        task=task,
        coordination_mode="feedback",
        max_feedback_rounds=3
    )
    
    # 执行任务
    print("\n开始执行任务...")
    result = await multi_agent_graph.ainvoke(initial_state)
    
    # 输出结果
    print("\n执行结果:")
    print(f"- 是否完成: {result.get('is_finished')}")
    print(f"- 反馈轮次: {result.get('feedback_round')}")
    print(f"- 评审通过: {result.get('review_passed')}")
    
    # 输出评审结果
    review_result = result.get('review_result', {})
    if review_result:
        print(f"- 评审分数: {review_result.get('score', 'N/A')}")
        print(f"- 改进建议: {review_result.get('suggestions', [])}")
    
    return result


async def example_3_research_task():
    """
    示例 3: 研究任务
    
    场景: 技术调研
    """
    print("\n" + "=" * 60)
    print("示例 3: 技术调研 - LangGraph 深度研究")
    print("=" * 60)
    
    # 定义任务
    task = {
        "description": "深入研究 LangGraph 框架并生成技术报告",
        "type": "research",
        "topic": "LangGraph 多智能体框架",
        "requirements": [
            "技术原理和架构",
            "核心特性和优势",
            "应用场景和案例",
            "最佳实践建议"
        ]
    }
    
    # 创建初始状态
    initial_state = create_initial_state(
        task=task,
        coordination_mode="sequential",
        max_iterations=10
    )
    
    # 执行任务
    print("\n开始执行任务...")
    result = await multi_agent_graph.ainvoke(initial_state)
    
    # 输出结果
    print("\n执行结果:")
    print(f"- 是否完成: {result.get('is_finished')}")
    
    # 输出研究结果
    final_result = result.get('final_result', {})
    if final_result:
        print(f"- 研究主题: {final_result.get('topic', 'N/A')}")
        print(f"- 研究摘要: {final_result.get('summary', 'N/A')[:200]}...")
    
    return result


async def example_4_custom_workflow():
    """
    示例 4: 自定义工作流
    
    场景: 使用单个智能体
    """
    print("\n" + "=" * 60)
    print("示例 4: 使用单个智能体")
    print("=" * 60)
    
    from src.agent.multi_agent.agents import AnalystAgent, PlannerAgent
    
    # 创建智能体
    analyst = AnalystAgent()
    planner = PlannerAgent()
    
    # 1. 使用分析师分析需求
    print("\n步骤 1: 分析需求")
    analysis_result = await analyst.analyze_requirements(
        "用户希望有一个简单易用的任务管理工具"
    )
    print(f"分析结果: {analysis_result.get('analysis', 'N/A')[:200]}...")
    
    # 2. 使用规划师制定计划
    print("\n步骤 2: 制定计划")
    plan = await planner.decompose_task(
        "开发一个任务管理工具"
    )
    print(f"计划步骤数: {len(plan)}")
    for i, step in enumerate(plan[:3], 1):
        print(f"  {i}. {step.get('description', step)}")
    
    return {"analysis": analysis_result, "plan": plan}


async def example_5_agent_registry():
    """
    示例 5: 智能体注册中心使用
    
    演示如何查询和管理智能体
    """
    print("\n" + "=" * 60)
    print("示例 5: 智能体注册中心")
    print("=" * 60)
    
    # 获取所有智能体
    all_agents = agent_registry.get_all_agents()
    print(f"\n注册的智能体总数: {len(all_agents)}")
    
    # 按类型查询
    from src.agent.multi_agent.base_agent import AgentType
    
    analysts = agent_registry.get_agents_by_type(AgentType.ANALYST)
    print(f"分析师数量: {len(analysts)}")
    
    executors = agent_registry.get_agents_by_type(AgentType.EXECUTOR)
    print(f"执行者数量: {len(executors)}")
    
    # 按能力查询
    agents_with_planning = agent_registry.get_agents_by_capability("任务分解")
    print(f"具有'任务分解'能力的智能体: {len(agents_with_planning)}")
    
    # 获取统计信息
    stats = agent_registry.get_statistics()
    print(f"\n统计信息:")
    print(f"- 总数: {stats['total_agents']}")
    print(f"- 按类型: {stats['agents_by_type']}")
    print(f"- 按状态: {stats['agents_by_status']}")
    
    return stats


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("多智能体系统示例")
    print("=" * 60)
    
    try:
        # 运行示例
        print("\n选择要运行的示例:")
        print("1. 顺序协作模式 - 产品需求分析")
        print("2. 反馈协作模式 - 代码生成与优化")
        print("3. 技术调研")
        print("4. 使用单个智能体")
        print("5. 智能体注册中心")
        print("6. 运行所有示例")
        
        choice = input("\n请输入选项 (1-6): ").strip()
        
        if choice == "1":
            await example_1_sequential_mode()
        elif choice == "2":
            await example_2_feedback_mode()
        elif choice == "3":
            await example_3_research_task()
        elif choice == "4":
            await example_4_custom_workflow()
        elif choice == "5":
            await example_5_agent_registry()
        elif choice == "6":
            # 运行所有示例
            await example_1_sequential_mode()
            await example_2_feedback_mode()
            await example_3_research_task()
            await example_4_custom_workflow()
            await example_5_agent_registry()
        else:
            print("无效的选项")
            return
        
        print("\n" + "=" * 60)
        print("示例执行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

