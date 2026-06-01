from fastapi import APIRouter

from .status_routes import status_router

def create_api_routes() -> APIRouter:
    """
    创建 API 路由，涵盖整个项目的所有路由管理
    """
    # 1.创建 APIRouter 实例
    api_router = APIRouter()

    # 2.将各个模块的路由添加到 APIRouter 实例中
    api_router.include_router(status_router)

    # 3.返回 APIRouter 实例
    return api_router

api_router = create_api_routes()