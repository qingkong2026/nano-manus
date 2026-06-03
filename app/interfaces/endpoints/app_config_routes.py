import logging

from fastapi import APIRouter, Depends

from app.application.services import AppConfigService
from app.domain.models import LLMConfig
from app.interfaces.dependencies import get_app_config_service
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
    app_config_service: AppConfigService = Depends(get_app_config_service)
):
    """
    更新LLM配置信息
    """
    update_llm_config = app_config_service.update_llm_config(new_llm_config)
    return Response.success(
        msg="更新LLM信息配置成功",
        data=update_llm_config.model_dump(exclude={"api_key"})
    )
