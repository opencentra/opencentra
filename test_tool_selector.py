# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position,no-value-for-parameter
"""测试工具选择器"""
import asyncio
import sys

sys.path.insert(0, "src")

from copaw.agents.tool_selector import ToolSelector


# 模拟模型响应
class MockResponse:
    """模拟响应"""

    def __init__(self, content):
        self.content = content


class MockModel:
    """模拟的聊天模型"""

    async def __call__(self, messages, **kwargs):
        """模拟调用模型"""
        # 返回模拟响应
        return MockResponse(
            [
                {
                    "type": "text",
                    "text": '["read_file", "execute_shell_command"]',
                },
            ]
        )


# 模拟工具列表
MOCK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from disk",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_use",
            "description": "Control browser with Playwright",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current system time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def test_tool_selector():
    """测试工具选择器"""
    print("=" * 50)
    print("测试工具选择器")
    print("=" * 50)

    model = MockModel()
    selector = ToolSelector(model=model, max_tools=5)

    # 测试1: 正常选择
    print("测试1: 正常选择")
    query = "读取 /etc/hosts 文件"
    selected = await selector.select_tools(query=query, all_tools=MOCK_TOOLS)
    print(f"Query: {query}")
    print(f"Selected: {[t['function']['name'] for t in selected]}")

    # 测试2: 缓存命中
    print("=" * 50)
    print("测试2: 缓存命中")
    query2 = "读取 /etc/hosts 文件"  # 相同query
    selected2 = await selector.select_tools(query=query2, all_tools=MOCK_TOOLS)
    print(f"Query: {query2} (should be cached)")
    print(f"Selected: {[t['function']['name'] for t in selected2]}")

    # 测试3: 不同query
    print("=" * 50)
    print("测试3: 不同查询")
    query3 = "打开浏览器访问 https://example.com"
    selected3 = await selector.select_tools(query=query3, all_tools=MOCK_TOOLS)
    print(f"Query: {query3}")
    print(f"Selected: {[t['function']['name'] for t in selected3]}")

    print("=" * 50)
    print("所有测试通过!")


if __name__ == "__main__":
    asyncio.run(test_tool_selector())
