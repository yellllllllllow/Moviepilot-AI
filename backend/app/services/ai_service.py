import json
from typing import AsyncGenerator, List, Dict, Any

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.log import logger

DEFAULT_SYSTEM_PROMPT = """你是一个 MoviePilot 媒体库管理助手。你可以帮助用户完成以下操作：

1. **搜索资源**：在 PT 站点搜索电影/电视剧资源
2. **添加订阅**：订阅媒体，自动监控新资源
3. **管理下载**：查看、暂停、恢复、删除下载任务
4. **媒体整理**：触发媒体库整理和刮削
5. **查看状态**：查看系统状态、磁盘空间、下载进度

使用规则：
- 用户说"搜索"、"找资源"、"有没有" → 先搜索再给出结果
- 用户说"订阅"、"追剧"、"添加到" → 添加订阅
- 用户说"下载" → 添加下载任务
- 用户说"整理"、"刮削" → 触发整理
- 回复时用中文，友好简洁
- 搜索到资源后，列出前 5 个最佳结果（包含标题、大小、做种数）
- 如果用户没有指定清晰度，默认优先推荐 4K/1080P"""


class AiService:
    """AI 服务核心类"""

    @staticmethod
    async def fetch_models(api_base_url: str, api_key: str) -> List[Dict]:
        """从服务商获取可用模型列表"""
        url = f"{api_base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # 兼容不同服务商的返回格式
        models = data.get("data", [])
        # 过滤出对话模型（排除 embedding, reranker, image 等）
        exclude_keywords = ["embedding", "reranker", "image"]
        chat_models = [
            m for m in models 
            if m.get("id") and not any(kw in m.get("id", "").lower() for kw in exclude_keywords)
        ]
        return chat_models

    @staticmethod
    async def test_connection(api_base_url: str, api_key: str, model_name: str) -> bool:
        """测试 AI 连接"""
        try:
            llm = ChatOpenAI(
                model=model_name,
                base_url=api_base_url,
                api_key=api_key,
                max_tokens=50,
            )
            response = await llm.ainvoke([HumanMessage(content="Hello")])
            return True
        except Exception as e:
            raise Exception(f"连接失败: {str(e)}")

    @staticmethod
    async def get_moviepilot_tools(api_token: str) -> List:
        """获取 MoviePilot MCP 工具并转换为 LangChain Tools"""
        from functools import wraps

        mcp_base_url = f"http://localhost:{settings.PORT}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{mcp_base_url}/api/v1/mcp/tools",
                headers={"X-API-KEY": api_token}
            )
            resp.raise_for_status()
            mcp_tools_data = resp.json()

        langchain_tools = []
        
        # 实际返回可能是列表或包含 tools 字段的对象
        mcp_tools = mcp_tools_data
        if isinstance(mcp_tools_data, dict):
            mcp_tools = mcp_tools_data.get("tools", mcp_tools_data.get("result", []))

        for mcp_tool in mcp_tools:
            tool_name = mcp_tool.get("name", "")
            if not tool_name:
                continue
            tool_desc = mcp_tool.get("description", "")
            input_schema = mcp_tool.get("input_schema", {})

            # 使用闭包捕获变量
            async def _make_tool_call(name=tool_name):
                async def _call_tool(**kwargs):
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"{mcp_base_url}/api/v1/mcp/tools/call",
                            headers={"X-API-KEY": api_token},
                            json={"tool_name": name, "arguments": kwargs}
                        )
                        result = resp.json()
                        if result.get("success"):
                            return result.get("result", "操作完成")
                        return f"操作失败: {result.get('error', '未知错误')}"
                return _call_tool

            tool_func = await _make_tool_call(tool_name)
            
            langchain_tools.append(
                StructuredTool.from_function(
                    name=tool_name,
                    description=tool_desc,
                    coroutine=tool_func,
                )
            )

        return langchain_tools

    @staticmethod
    async def chat_stream(
        session_id: int,
        message: str,
        provider_config: Dict,
        api_token: str,
        history_messages: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """流式对话，生成 SSE 事件"""
        # 1. 创建 LLM
        llm = ChatOpenAI(
            model=provider_config["model_name"],
            base_url=provider_config["api_base_url"],
            api_key=provider_config["api_key"],
            temperature=provider_config.get("temperature", 0.7),
            max_tokens=provider_config.get("max_tokens", 4096),
            streaming=True,
        )

        # 2. 获取 MoviePilot 工具
        tools = await AiService.get_moviepilot_tools(api_token)

        # 3. 构建系统提示词
        system_prompt = provider_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
        if tools:
            system_prompt += "\n\n你可以使用以下工具来操控 MoviePilot：\n"
            for tool in tools:
                system_prompt += f"- {tool.name}: {tool.description}\n"

        # 4. 构建消息列表
        messages = [SystemMessage(content=system_prompt)]
        if history_messages:
            for h in history_messages[-20:]:  # 最近 20 条
                if h["role"] == "user":
                    messages.append(HumanMessage(content=h["content"]))
                elif h["role"] == "assistant":
                    messages.append(AIMessage(content=h["content"]))

        messages.append(HumanMessage(content=message))

        # 5. 使用 langgraph 创建 agent
        agent = create_react_agent(llm, tools)

        # 6. 流式执行
        full_response = ""
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2"
            ):
                kind = event.get("event")

                # 工具调用开始
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event.get("data", {}).get("input", {})
                    yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'args': tool_input})}\n\n"

                # 工具调用结束
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output", "")
                    yield f"event: tool_end\ndata: {json.dumps({'tool': tool_name, 'result': str(tool_output)})}\n\n"

                # LLM 输出 token
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", {})
                    if hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
                        yield f"event: delta\ndata: {json.dumps({'content': chunk.content})}\n\n"

        except Exception as e:
            logger.error(f"AI 对话流式处理出错: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        # 7. 完成
        yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'full_response': full_response})}\n\n"
