import logging

from fastapi import APIRouter, Depends, Body
from typing import Dict, Optional

from app.application.services import AppConfigService
from app.domain.models import AgentConfig, LLMConfig, MCPConfig
from app.interfaces.schema.app_config import ListMCPServerResponse
from app.interfaces.service_dependencies import get_app_config_service
from app.interfaces.schema import Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/app-config", tags=["设置模块"])


@router.get(
    path="/llm",
    response_model=Response[LLMConfig],
    summary="获取LLM配置信息",
    description="包含LLM供应商的 base_url、temperature、model_name、max_tokens",
)
async def get_llm_config(
    app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[LLMConfig]:
    """
    获取LLM配置信息
    """
    llm_config: LLMConfig = app_config_service.get_llm_config()
    return Response.success(data=llm_config.model_dump(exclude={"api_key"}))


@router.post(
    path="/llm",
    response_model=Response[LLMConfig],
    summary="更新LLM配置信息",
    description="更新LLM配置信息，当 api_key 为空时表示不更新该字段",
)
async def update_llm_config(
    new_llm_config: LLMConfig,
    app_config_service: AppConfigService = Depends(get_app_config_service),
):
    """
    更新LLM配置信息
    """
    update_llm_config = app_config_service.update_llm_config(new_llm_config)
    return Response.success(
        msg="更新LLM信息配置成功",
        data=update_llm_config.model_dump(exclude={"api_key"}),
    )


@router.get(
    path="/agent",
    response_model=Response[AgentConfig],
    summary="获取Agent通用配置信息",
    description="包含最大迭代次数、最大重试次数、最大搜索次数",
)
async def get_agent_config(
    app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[AgentConfig]:
    """
    获取LLM配置信息
    """
    agent_config: AgentConfig = app_config_service.get_agent_config()
    return Response.success(data=agent_config.model_dump())


@router.post(
    path="/agent",
    response_model=Response[AgentConfig],
    summary="更新Agent通用配置信息",
    description="更新Agent配置信息",
)
async def update_agent_config(
    new_agent_config: AgentConfig,
    app_config_service: AppConfigService = Depends(get_app_config_service),
):
    """
    更新LLM配置信息
    """
    update_agent_config = app_config_service.update_agent_config(new_agent_config)
    return Response.success(
        msg="更新Agent通用配置成功", data=update_agent_config.model_dump()
    )

@router.get(
    path="/mcp-servers",
    response_model=Response[ListMCPServerResponse],
    summary="获取MCP服务器工具列表",
    description="获取当前系统的MCP服务器列表，包含MCP服务名字、工具列表、启用状态等。"
)
async def get_mcp_servers(
        app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[ListMCPServerResponse]:
    """获取当前系统的MCP服务器工具列表"""
    mcp_servers = await app_config_service.get_mcp_servers()
    return Response.success(
        msg="获取mcp服务器列表成功",
        data=ListMCPServerResponse(mcp_servers=mcp_servers),
    )

@router.post(
    path="/mcp-servers",
    response_model=Response[Optional[Dict]],
    summary="新增MCP服务配置，支持传递一个或者多个配置",
    description="传递MCP配置信息为系统新增MCP工具"
)
async def create_mcp_server(
        mcp_config: MCPConfig,
        app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[Optional[Dict]]:
    """根据传递的配置信息创建 mcp 服务"""
    app_config_service.update_and_create_mcp_servers(mcp_config)
    return Response.success(msg="新增MCP服务配置成功")

@router.post(
    path="/mcp-servers/{server_name}/delete",
    response_model=Response[Optional[Dict]],
    summary="删除MCP服务配置",
    description="根据传递的MCP服务名字删除指定的MCP服务"
)
async def delete_mcp_server(
        server_name: str,
        app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[Optional[Dict]]:
    """根据服务名字删除MCP服务器"""
    app_config_service.delete_mcp_servers(server_name)
    return Response.success(msg="删除 MCP 服务配置成功")

@router.post(
    path="/mcp-servers/{server_name}/enabled",
    response_model=Response[Optional[Dict]],
    summary="更新MCP服务的启用状态",
    description="根据传递的server_name+enabled更新指定MCP服务的启用状态"
)
async def set_mcp_server_enabled(
        server_name: str,
        enabled: bool = Body(...),
        app_config_service: AppConfigService = Depends(get_app_config_service),
) -> Response[Optional[Dict]]:
    """根据传递的 server_name+enabled 更新 MCP 启用状态"""
    app_config_service.set_mcp_server_enabled(server_name, enabled)
    return Response.success(msg="更新 MCP 服务启用状态成功")