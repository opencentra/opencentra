# -*- coding: utf-8 -*-
"""API routes for MCP (Model Context Protocol) clients management."""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional, Literal, Any

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel, Field

from agentscope.mcp import HttpStatefulClient, StdIOStatefulClient

from ...config import load_config, save_config
from ...config.config import MCPClientConfig

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPClientInfo(BaseModel):
    """MCP client information for API responses."""

    key: str = Field(..., description="Unique client key identifier")
    name: str = Field(..., description="Client display name")
    description: str = Field(default="", description="Client description")
    enabled: bool = Field(..., description="Whether the client is enabled")
    transport: Literal["stdio", "streamable_http", "sse"] = Field(
        ...,
        description="MCP transport type",
    )
    url: str = Field(
        default="",
        description="Remote MCP endpoint URL (for HTTP/SSE transports)",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers for remote transport",
    )
    command: str = Field(
        default="",
        description="Command to launch the MCP server",
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command-line arguments",
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )
    cwd: str = Field(
        default="",
        description="Working directory for stdio MCP command",
    )


class MCPClientCreateRequest(BaseModel):
    """Request body for creating/updating an MCP client."""

    name: str = Field(..., description="Client display name")
    description: str = Field(default="", description="Client description")
    enabled: bool = Field(
        default=True,
        description="Whether to enable the client",
    )
    transport: Literal["stdio", "streamable_http", "sse"] = Field(
        default="stdio",
        description="MCP transport type",
    )
    url: str = Field(
        default="",
        description="Remote MCP endpoint URL (for HTTP/SSE transports)",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers for remote transport",
    )
    command: str = Field(
        default="",
        description="Command to launch the MCP server",
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command-line arguments",
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )
    cwd: str = Field(
        default="",
        description="Working directory for stdio MCP command",
    )


class MCPClientUpdateRequest(BaseModel):
    """Request body for updating an MCP client (all fields optional)."""

    name: Optional[str] = Field(None, description="Client display name")
    description: Optional[str] = Field(None, description="Client description")
    enabled: Optional[bool] = Field(
        None,
        description="Whether to enable the client",
    )
    transport: Optional[Literal["stdio", "streamable_http", "sse"]] = Field(
        None,
        description="MCP transport type",
    )
    url: Optional[str] = Field(
        None,
        description="Remote MCP endpoint URL (for HTTP/SSE transports)",
    )
    headers: Optional[Dict[str, str]] = Field(
        None,
        description="HTTP headers for remote transport",
    )
    command: Optional[str] = Field(
        None,
        description="Command to launch the MCP server",
    )
    args: Optional[List[str]] = Field(
        None,
        description="Command-line arguments",
    )
    env: Optional[Dict[str, str]] = Field(
        None,
        description="Environment variables",
    )
    cwd: Optional[str] = Field(
        None,
        description="Working directory for stdio MCP command",
    )


def _mask_env_value(value: str) -> str:
    """
    Mask environment variable value showing first 2-3 chars and last 4 chars.

    Examples:
        sk-proj-1234567890abcdefghij1234 -> sk-****************************1234
        abc123456789xyz -> ab***********xyz (if no dash)
        my-api-key-value -> my-************lue
        short123 -> ******** (8 chars or less, fully masked)
    """
    if not value:
        return value

    length = len(value)
    if length <= 8:
        # For short values, just mask everything
        return "*" * length

    # Show first 2-3 characters (3 if there's a dash at position 2)
    prefix_len = 3 if length > 2 and value[2] == "-" else 2
    prefix = value[:prefix_len]

    # Show last 4 characters
    suffix = value[-4:]

    # Calculate masked section length (at least 4 asterisks)
    masked_len = max(length - prefix_len - 4, 4)

    return f"{prefix}{'*' * masked_len}{suffix}"


def _build_client_info(key: str, client: MCPClientConfig) -> MCPClientInfo:
    """Build MCPClientInfo from config with masked env values."""
    # Mask environment variable values for security
    masked_env = (
        {k: _mask_env_value(v) for k, v in client.env.items()}
        if client.env
        else {}
    )
    masked_headers = (
        {k: _mask_env_value(v) for k, v in client.headers.items()}
        if client.headers
        else {}
    )

    # Mask header values for security (especially Authorization)
    masked_headers = {}
    if client.headers:
        for k, v in client.headers.items():
            if k.lower() in ("authorization", "api-key", "token"):
                masked_headers[k] = _mask_env_value(v)
            else:
                masked_headers[k] = v

    return MCPClientInfo(
        key=key,
        name=client.name,
        description=client.description,
        enabled=client.enabled,
        transport=client.transport,
        url=client.url,
        headers=masked_headers,
        command=client.command,
        args=client.args,
        env=masked_env,
        cwd=client.cwd,
    )


@router.get(
    "",
    response_model=List[MCPClientInfo],
    summary="List all MCP clients",
)
async def list_mcp_clients() -> List[MCPClientInfo]:
    """Get list of all configured MCP clients."""
    config = load_config()
    return [
        _build_client_info(key, client)
        for key, client in config.mcp.clients.items()
    ]


@router.get(
    "/{client_key}",
    response_model=MCPClientInfo,
    summary="Get MCP client details",
)
async def get_mcp_client(client_key: str = Path(...)) -> MCPClientInfo:
    """Get details of a specific MCP client."""
    config = load_config()
    client = config.mcp.clients.get(client_key)
    if client is None:
        raise HTTPException(404, detail=f"MCP client '{client_key}' not found")
    return _build_client_info(client_key, client)


@router.post(
    "",
    response_model=MCPClientInfo,
    summary="Create a new MCP client",
    status_code=201,
)
async def create_mcp_client(
    client_key: str = Body(..., embed=True),
    client: MCPClientCreateRequest = Body(..., embed=True),
) -> MCPClientInfo:
    """Create a new MCP client configuration."""
    config = load_config()

    # Check if client already exists
    if client_key in config.mcp.clients:
        raise HTTPException(
            400,
            detail=f"MCP client '{client_key}' already exists. Use PUT to "
            f"update.",
        )

    # Create new client config
    new_client = MCPClientConfig(
        name=client.name,
        description=client.description,
        enabled=client.enabled,
        transport=client.transport,
        url=client.url,
        headers=client.headers,
        command=client.command,
        args=client.args,
        env=client.env,
        cwd=client.cwd,
    )

    # Add to config and save
    config.mcp.clients[client_key] = new_client
    save_config(config)

    return _build_client_info(client_key, new_client)


@router.put(
    "/{client_key}",
    response_model=MCPClientInfo,
    summary="Update an MCP client",
)
async def update_mcp_client(
    client_key: str = Path(...),
    updates: MCPClientUpdateRequest = Body(...),
) -> MCPClientInfo:
    """Update an existing MCP client configuration."""
    config = load_config()

    # Check if client exists
    existing = config.mcp.clients.get(client_key)
    if existing is None:
        raise HTTPException(404, detail=f"MCP client '{client_key}' not found")

    # Update fields if provided
    update_data = updates.model_dump(exclude_unset=True)

    # Special handling for env: merge with existing, don't replace
    if "env" in update_data and update_data["env"] is not None:
        updated_env = existing.env.copy() if existing.env else {}
        updated_env.update(update_data["env"])
        update_data["env"] = updated_env

    merged_data = existing.model_dump(mode="json")
    merged_data.update(update_data)
    updated_client = MCPClientConfig.model_validate(merged_data)
    config.mcp.clients[client_key] = updated_client

    # Save updated config
    save_config(config)

    return _build_client_info(client_key, updated_client)


@router.patch(
    "/{client_key}/toggle",
    response_model=MCPClientInfo,
    summary="Toggle MCP client enabled status",
)
async def toggle_mcp_client(
    client_key: str = Path(...),
) -> MCPClientInfo:
    """Toggle the enabled status of an MCP client."""
    config = load_config()

    client = config.mcp.clients.get(client_key)
    if client is None:
        raise HTTPException(404, detail=f"MCP client '{client_key}' not found")

    # Toggle enabled status
    client.enabled = not client.enabled
    save_config(config)

    return _build_client_info(client_key, client)


@router.delete(
    "/{client_key}",
    response_model=Dict[str, str],
    summary="Delete an MCP client",
)
async def delete_mcp_client(
    client_key: str = Path(...),
) -> Dict[str, str]:
    """Delete an MCP client configuration."""
    config = load_config()

    if client_key not in config.mcp.clients:
        raise HTTPException(404, detail=f"MCP client '{client_key}' not found")

    # Remove client
    del config.mcp.clients[client_key]
    save_config(config)

    return {"message": f"MCP client '{client_key}' deleted successfully"}


# === Test Connection API ===
# MCP客户端连接测试API
# 功能：测试MCP客户端的连接状态，获取可用工具列表
# 前端调用：点击"Test Connection"按钮时触发 POST /api/mcp/{client_key}/test


class MCPToolInfo(BaseModel):
    """MCP工具信息模型

    用于存储单个MCP工具的元数据信息，包括工具名称、描述和输入参数schema。
    """

    name: str = Field(..., description="Tool name")
    description: str = Field(default="", description="Tool description")
    input_schema: dict = Field(
        default_factory=dict,
        description="JSON schema for tool input",
    )


class MCPTestResult(BaseModel):
    """MCP连接测试结果模型

    用于返回MCP客户端连接测试的结果，包括：
    - success: 连接是否成功
    - error: 错误信息（如果失败）
    - tools: 可用工具列表
    - connection_time_ms: 连接耗时（毫秒）
    """

    success: bool = Field(
        ..., description="Whether the connection test succeeded"
    )
    error: str | None = Field(
        default=None,
        description="Error message if connection failed",
    )
    tools: List[MCPToolInfo] = Field(
        default_factory=list,
        description="List of available tools from the MCP server",
    )
    connection_time_ms: float = Field(
        ...,
        description="Time taken to establish connection in milliseconds",
    )


@router.post(
    "/{client_key}/test",
    response_model=MCPTestResult,
    summary="Test MCP client connection",
)
async def test_mcp_client(
    client_key: str = Path(...),
) -> MCPTestResult:
    """测试MCP客户端连接并获取可用工具列表

    Args:
        client_key: MCP客户端的唯一标识key

    Returns:
        MCPTestResult: 包含连接状态、工具列表和连接耗时的结果对象

    功能说明：
        1. 根据client_key获取MCP客户端配置
        2. 根据transport类型（stdio/streamable_http/sse）创建对应的客户端
        3. 建立连接（超时30秒）
        4. 获取MCP服务器提供的工具列表
        5. 关闭连接并返回结果

    前端调用示例：
        POST /api/mcp/ecom-mcp/test
    """
    config = load_config()
    client_config = config.mcp.clients.get(client_key)

    if client_config is None:
        raise HTTPException(404, detail=f"MCP client '{client_key}' not found")

    start_time = time.time()

    try:
        # 根据transport类型创建对应的MCP客户端
        # stdio: 本地进程通信，通过command/args启动子进程
        # streamable_http/sse: 远程HTTP连接，通过url连接MCP服务器
        if client_config.transport == "stdio":
            client = StdIOStatefulClient(
                name=client_config.name,
                command=client_config.command,
                args=client_config.args,
                env=client_config.env,
                cwd=client_config.cwd or None,
            )
        else:
            # HTTP/SSE transport - 远程MCP服务器
            client = HttpStatefulClient(
                name=client_config.name,
                transport=client_config.transport,
                url=client_config.url,
                headers=client_config.headers or None,
            )

        # 建立连接，设置30秒超时
        await asyncio.wait_for(client.connect(), timeout=30.0)

        # 获取MCP服务器提供的工具列表（异步方法）
        tools_raw = await client.list_tools()
        tools = []
        for tool in tools_raw:
            # 兼容不同的属性名：inputSchema（官方）和 input_schema（部分实现）
            input_schema = (
                getattr(tool, "inputSchema", None)
                or getattr(tool, "input_schema", None)
                or {}
            )
            tools.append(
                MCPToolInfo(
                    name=getattr(tool, "name", "unknown"),
                    description=getattr(tool, "description", "") or "",
                    input_schema=input_schema,
                ),
            )

        # 关闭客户端连接（忽略关闭错误）
        try:
            await client.close()
        except Exception:
            pass

        elapsed = (time.time() - start_time) * 1000

        return MCPTestResult(
            success=True,
            error=None,
            tools=tools,
            connection_time_ms=round(elapsed, 1),
        )

    except asyncio.TimeoutError:
        # 连接超时（30秒）
        elapsed = (time.time() - start_time) * 1000
        return MCPTestResult(
            success=False,
            error="Connection timeout after 30 seconds",
            tools=[],
            connection_time_ms=round(elapsed, 1),
        )
    except Exception as e:
        # 其他错误：网络问题、MCP服务器错误等
        elapsed = (time.time() - start_time) * 1000
        return MCPTestResult(
            success=False,
            error=str(e),
            tools=[],
            connection_time_ms=round(elapsed, 1),
        )
