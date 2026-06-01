from fastapi import FastAPI
from pydantic import BaseModel

from app.interfaces.schema import Response
from core.config import get_settings

# 1.加载配置信息
settings = get_settings()

app = FastAPI()


class User(BaseModel):
    id: int
    name: str
    age: int


repository = {
    1: User(id=1, name="John", age=30),
    2: User(id=2, name="Jane", age=25),
    3: User(id=3, name="Bob", age=40),
}


@app.get("/users/{user_id}", response_model=Response[User])
async def get_user(user_id: int):
    user = repository.get(user_id)
    if user:
        return Response.success(data=user)
    return Response.error(code=404, msg="User not found")


@app.get("/users", response_model=Response[list[User]])
async def get_all_users():
    users = list(repository.values())
    return Response.success(data=users)
