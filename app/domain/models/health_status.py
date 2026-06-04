from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """健康监控状态"""

    service: str = Field(default="", description="服务名称")
    status: str = Field(default="", description="服务状态。ok表示正常，error表示异常")
    timestamp: int = Field(default=0, description="状态更新时间戳")
    details: str = Field(default="", description="出错时的详细信息")
