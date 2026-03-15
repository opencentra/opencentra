# -*- coding: utf-8 -*-
"""Tool Selector - 动态工具选择模块（激进模式）

完全由LLM选择工具，带缓存机制：
1. 检查缓存是否有相同query的选择结果
2. 无缓存则发送工具摘要让LLM选择
3. 缓存选择结果
4. 只发送选中的工具完整schema

这样可以大幅减少请求token，提高工具选择准确性。
"""

import hashlib
import json
import logging
import re
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# 激进模式：没有核心工具，完全由LLM决定
# 最大选择工具数量
MAX_TOOLS = 15

# 缓存大小限制
CACHE_MAX_SIZE = 100

# Fallback 默认核心工具（当 LLM 选择失败时使用）
FALLBACK_TOOLS = {
    "read_file",
    "write_file",
    "edit_file",
    "execute_shell_command",
    "browser_use",
    "get_current_time",
    "desktop_screenshot",
}

# 工具选择prompt模板 - 优化版本，更直接明确
TOOL_SELECTION_PROMPT = """You are a tool selector. Your ONLY job is to output a JSON array of tool names.

User query: {query}

{skills_section}Available tools:
{tool_list}

Instructions:
1. Select tools that help with the user query
2. Maximum {max_tools} tools
3. If a Skill matches, prefer the skill name
4. Output ONLY a JSON array like: ["tool_name1", "tool_name2"]
5. Do NOT write any explanation or other text

JSON array:"""


class ToolSelector:
    """动态工具选择器 - 激进模式

    完全由LLM选择工具，带LRU缓存
    """

    def __init__(self, model, toolkit, max_tools: int = MAX_TOOLS):
        """初始化工具选择器

        Args:
            model: 语言模型实例（与主任务使用同一个）
            toolkit: Toolkit实例，用于获取skills信息
            max_tools: 最多选择的工具数量
        """
        self.model = model
        self.toolkit = toolkit
        self.max_tools = max_tools
        # 缓存: query_hash -> selected_tool_names
        self._cache: Dict[str, List[str]] = {}

    def _get_query_hash(self, query: str, tool_names: List[str]) -> str:
        """计算查询的缓存key

        基于query内容和可用工具列表生成hash
        """
        content = f"{query}|{','.join(sorted(tool_names))}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_tool_summary(self, tool_schema: dict) -> str:
        """获取工具的简要描述"""
        func = tool_schema.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        # 只取第一句或前80字符
        first_sentence = desc.split("。")[0].split("\n")[0][:80]
        return f"{name} - {first_sentence}"

    def _get_skills_info(self) -> str:
        """获取skills信息,按照agentscope默认格式输出"""
        if (
            not self.toolkit
            or not hasattr(self.toolkit, "skills")
            or not self.toolkit.skills
        ):
            return ""

        # agentscope默认的skill instruction
        skill_instruction = (
            "# Agent Skills\n"
            "The agent skills are a collection of folds of instructions, scripts, "
            "and resources that you can load dynamically to improve performance "
            "on specialized tasks. Each agent skill has a `SKILL.md` file in its "
            "folder that describes how to use the skill. If you want to use a "
            "skill, you MUST read its `SKILL.md` file carefully."
        )

        skill_descriptions = [skill_instruction]

        for skill_name, skill in self.toolkit.skills.items():
            # AgentSkill 是 TypedDict, 用字典方式访问
            name = (
                skill.get("name", skill_name)
                if isinstance(skill, dict)
                else getattr(skill, "name", skill_name)
            )
            desc = (
                skill.get("description", "")
                if isinstance(skill, dict)
                else getattr(skill, "description", "")
            )
            skill_dir = (
                skill.get("dir", "")
                if isinstance(skill, dict)
                else getattr(skill, "dir", "")
            )

            # 按照agentscope默认模板格式
            skill_descriptions.append(
                f'## {name}\n{desc}\nCheck "{skill_dir}/SKILL.md" for how to use this skill'
            )

        return "\n".join(skill_descriptions)

    def _evict_cache_if_needed(self):
        """LRU缓存淘汰"""
        if len(self._cache) > CACHE_MAX_SIZE:
            # 删除一半（简单的FIFO，够用了）
            keys_to_remove = list(self._cache.keys())[: CACHE_MAX_SIZE // 2]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"Cache evicted {len(keys_to_remove)} entries")

    async def select_tools(
        self,
        query: str,
        all_tools: List[dict],
    ) -> List[dict]:
        """选择相关工具

        Args:
            query: 用户问题
            all_tools: 所有可用工具的schema列表

        Returns:
            选中的工具schema列表

        Raises:
            RuntimeError: 工具选择失败时抛出
        """
        if not all_tools:
            return []

        # 构建工具名称到schema的映射
        tool_map: Dict[str, dict] = {}
        for tool in all_tools:
            name = tool.get("function", {}).get("name", "")
            if name:
                tool_map[name] = tool

        all_tool_names = list(tool_map.keys())

        # 1. 检查缓存
        cache_key = self._get_query_hash(query, all_tool_names)
        if cache_key in self._cache:
            cached_names = self._cache[cache_key]
            result = [tool_map[n] for n in cached_names if n in tool_map]
            logger.info(
                f"Tool selection (cached): {len(result)}/{len(all_tools)} tools - "
                f"{cached_names}",
            )
            return result

        # 2. LLM选择（带 fallback）
        selected_names = None
        try:
            selected_names = await self._llm_select(
                query=query, tool_map=tool_map
            )
        except Exception as e:
            logger.warning(f"LLM tool selection failed, using fallback: {e}")
            # Fallback: 使用默认核心工具
            selected_names = FALLBACK_TOOLS.intersection(tool_map.keys())
            if not selected_names:
                # 如果默认工具都不存在，取前 10 个工具
                selected_names = set(all_tool_names[:10])
            logger.info(f"Using fallback tools: {selected_names}")

        if not selected_names:
            # 最后的 fallback：使用所有工具
            selected_names = set(all_tool_names)
            logger.warning("No tools selected, using all tools as fallback")

        # 3. 缓存结果（稍后在处理完skill后更新）
        # 先不缓存，等处理完skill后再缓存最终结果

        # 4. 处理skill名：如果选择了skill，提取SKILL.md中的工具名
        final_tool_names = set()
        for name in selected_names:
            if name in tool_map:
                # 是实际工具名，直接添加
                final_tool_names.add(name)
            else:
                # 可能是skill名，尝试提取工具
                skill_tools = self._extract_tools_from_skill(name, tool_map)
                if skill_tools:
                    final_tool_names.update(skill_tools)
                    logger.info(
                        f"Extracted tools from skill '{name}': {skill_tools}"
                    )

        # 5. 构建结果
        result = [tool_map[n] for n in final_tool_names if n in tool_map]

        # 6. 缓存最终结果
        self._evict_cache_if_needed()
        self._cache[cache_key] = list(final_tool_names)

        logger.info(
            f"Tool selection (LLM): {len(result)}/{len(all_tools)} tools - "
            f"{list(final_tool_names)}",
        )

        return result

    def _extract_tools_from_skill(
        self, skill_name: str, tool_map: Dict[str, dict]
    ) -> Set[str]:
        """从SKILL.md中提取工具名

        Args:
            skill_name: skill名称
            tool_map: 可用工具映射

        Returns:
            提取到的工具名集合
        """
        if (
            not self.toolkit
            or not hasattr(self.toolkit, "skills")
            or not self.toolkit.skills
        ):
            return set()

        # 查找skill
        skill = self.toolkit.skills.get(skill_name)
        if not skill:
            return set()

        # 获取skill目录
        skill_dir = (
            skill.get("dir", "")
            if isinstance(skill, dict)
            else getattr(skill, "dir", "")
        )
        if not skill_dir:
            return set()

        # 读取SKILL.md
        skill_md_path = f"{skill_dir}/SKILL.md"
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(
                f"Failed to read SKILL.md for skill '{skill_name}': {e}"
            )
            return set()

        # 提取工具名：匹配markdown中的工具调用格式
        # 例如：`get_running_browsers()` 或 **get_running_browsers**
        extracted_tools = set()

        # 匹配 `tool_name()` 格式
        tool_calls = re.findall(r"`([a-z_][a-z0-9_]*)\s*\(\)", content)
        extracted_tools.update(tool_calls)

        # 匹配 **tool_name** 格式（加粗的工具名）
        bold_tools = re.findall(r"\*\*([a-z_][a-z0-9_]*)\*\*", content)
        extracted_tools.update(bold_tools)

        # 只保留在tool_map中存在的工具
        valid_tools = {t for t in extracted_tools if t in tool_map}

        return valid_tools

    async def _llm_select(
        self, query: str, tool_map: Dict[str, dict]
    ) -> Set[str]:
        """使用LLM选择工具

        Args:
            query: 用户问题
            tool_map: 工具名称到schema的映射

        Returns:
            选中的工具名称集合
        """
        # 构建工具摘要列表
        tool_summaries = []
        for name, tool in tool_map.items():
            summary = self._get_tool_summary(tool)
            tool_summaries.append(summary)

        tool_list = "\n".join(f"- {s}" for s in tool_summaries)

        # 获取skills信息，如果有skills则添加分隔符
        skills_info = self._get_skills_info()
        if skills_info:
            skills_section = skills_info + "\n\n"
        else:
            skills_section = ""

        prompt = TOOL_SELECTION_PROMPT.format(
            query=query,
            skills_section=skills_section,
            tool_list=tool_list,
            max_tools=self.max_tools,
        )

        try:
            # 调用模型（非流式，不传tools参数）
            # 模型通过 __call__ 方法调用
            response = await self.model(
                messages=[{"role": "user", "content": prompt}],
            )

            # 处理响应（可能是流式或非流式）
            content = ""
            if hasattr(response, "__aiter__"):
                # 流式响应
                async for chunk in response:
                    if chunk.content:
                        content += "".join(
                            block.get("text", "")
                            for block in chunk.content
                            if isinstance(block, dict)
                            and block.get("type") == "text"
                        )
            else:
                # 非流式响应
                content = "".join(
                    block.get("text", "")
                    for block in response.content
                    if isinstance(block, dict) and block.get("type") == "text"
                )

            logger.debug(f"LLM tool selection response: {content}")

            # 清理响应内容
            content = content.strip()

            # 移除可能的markdown代码块
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(
                    lines[1:-1] if lines[-1] == "```" else lines[1:]
                )

            # 提取JSON数组 - 尝试多种方式
            selected = None

            # 方式1: 找最后一个完整的 [...] 块
            # 使用非贪婪匹配找所有 [...] 块，取最后一个
            all_json_matches = re.findall(r"\[[^\[\]]*\]", content, re.DOTALL)
            if all_json_matches:
                # 从后往前尝试解析
                for match in reversed(all_json_matches):
                    try:
                        candidate = json.loads(match)
                        if isinstance(candidate, list):
                            selected = candidate
                            break
                    except json.JSONDecodeError:
                        continue

            # 方式2: 如果方式1失败，尝试更宽松的匹配
            if selected is None:
                # 找最后一个 [ 开始的块，尝试截取到合理位置
                last_bracket = content.rfind("[")
                if last_bracket != -1:
                    # 尝试找到匹配的 ]
                    bracket_content = content[last_bracket:]
                    # 尝试截取到第一个 ] 后
                    end_idx = bracket_content.find("]")
                    if end_idx != -1:
                        try:
                            candidate = json.loads(
                                bracket_content[: end_idx + 1]
                            )
                            if isinstance(candidate, list):
                                selected = candidate
                        except json.JSONDecodeError:
                            pass

            if selected:
                # 验证工具名称存在（工具名或skill名都有效）
                skill_names = set()
                if (
                    self.toolkit
                    and hasattr(self.toolkit, "skills")
                    and self.toolkit.skills
                ):
                    skill_names = set(self.toolkit.skills.keys())

                valid_selected = [
                    n
                    for n in selected
                    if isinstance(n, str)
                    and (n in tool_map or n in skill_names)
                ]
                if valid_selected:
                    return set(valid_selected)
                else:
                    logger.warning(f"LLM selected invalid tools: {selected}")

            raise ValueError(f"无法从响应中解析工具列表: {content[:200]}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise RuntimeError(f"工具选择失败：解析错误。请重新描述您的需求。") from e
        except Exception as e:
            logger.error(f"LLM tool selection failed: {e}")
            raise RuntimeError(f"工具选择失败：{e}。请重新描述您的需求。") from e

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("Tool selection cache cleared")


def compress_tool_schema(
    schema: dict, keep_description_length: int = 80
) -> dict:
    """压缩工具schema，减少token

    Args:
        schema: 原始工具schema
        keep_description_length: 保留的描述长度

    Returns:
        压缩后的schema
    """
    func = schema.get("function", {})

    # 压缩描述
    desc = func.get("description", "")
    if len(desc) > keep_description_length:
        desc = desc[:keep_description_length] + "..."

    # 压缩参数描述
    params = func.get("parameters", {})
    properties = params.get("properties", {})

    compressed_props = {}
    for key, value in properties.items():
        compressed_props[key] = {
            "type": value.get("type", "string"),
        }
        # 只保留简短描述
        if "description" in value:
            prop_desc = value["description"]
            if len(prop_desc) > 40:
                prop_desc = prop_desc[:40] + "..."
            compressed_props[key]["description"] = prop_desc

    return {
        "type": "function",
        "function": {
            "name": func.get("name", ""),
            "description": desc,
            "parameters": {
                "type": params.get("type", "object"),
                "required": params.get("required", []),
                "properties": compressed_props,
            },
        },
    }
