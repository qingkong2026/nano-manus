import asyncio
import logging
import uuid
from typing import Any, Optional, Tuple

from app.domain.external.message_queue import MessageQueue
from app.infrastructure.storage.redis import get_redis

logger = logging.getLogger(__name__)


class RedisMessageQueue(MessageQueue):
    """基于 Redis-Stream 实现的消息队列"""

    def __init__(self, stream_name: str) -> None:
        self._stream_name = stream_name
        self._redis = get_redis()
        self._lock_expire_seconds = 10

    async def _acquire_lock(
        self, lock_key: str, timeout_seconds: int = 5
    ) -> Optional[str]:
        """根据传递的 lock_key 构建一个分布式锁"""
        # 1.创建锁对应的值
        lock_value = str(uuid.uuid4())
        end_time = timeout_seconds

        # 2.使用 end_time 构建锁的过期时间
        while end_time > 0:
            # 3.使用 redis 的 setnx 方法设置锁
            result = await self._redis.client.set(
                lock_key, lock_value, nx=True, ex=self._lock_expire_seconds
            )

            # 4.如果设置成功，则返回锁的值
            if result:
                return lock_value

            # 5.睡眠指定时间并将 end_time 递减
            await asyncio.sleep(0.1)
            end_time -= 0.1

        return None

    async def _release_lock(self, lock_key: str, lock_value: str) -> bool:
        """根据传递的 lock_key 和 lock_value 释放锁"""
        # 1.构建一段 lua 脚本，用于释放锁
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            # 2.注册脚本
            script = self._redis.client.register_script(release_script)
            # 3.执行脚本，传入锁的 key 和 value
            result = await script(keys=[lock_key], args=[lock_value])
            return result == 1
        except Exception as e:
            logger.error(f"释放锁时发生错误：{e}")
            return False

    async def put(self, message: Any) -> str:
        """将消息放入队列"""
        logger.debug(f"往消息队列{self._stream_name}中添加一条消息：{message}")
        message_id = await self._redis.client.xadd(
            self._stream_name, {"data": message}
        )
        return message_id

    async def get(self, start_id: str = None, block_ms: int = None) -> Tuple[str, Any]:
        """从消息队列中获取一条消息"""
        logger.debug(
            f"从消息队列{self._stream_name}中获取一条消息，start_id={start_id}"
        )

        # 1.判断 start_id 是否为空
        if start_id is None:
            start_id = "0"

        try:
            # 2.从 Redis 中获取一条消息
            messages = await self._redis.client.xread(
                streams={self._stream_name: start_id}, count=1, block=block_ms
            )

            # 3.判断消息是否存在
            if messages is None:
                return None, None

            # 4.解析消息
            stream_message = messages[0][1]
            if not stream_message:
                return None, None

            # 5.提取 id 和数据
            message_id, message_data = stream_message[0]
            return message_id, message_data.get("data")
        except Exception as e:
            logger.error(f"从消息队列{self._stream_name}中获取消息失败：{e}")
            return None, None

    async def pop(self) -> Tuple[str, Any]:
        """获取并移除消息队列中的第一条消息"""
        logger.debug(f"从消息队列{self._stream_name}中获取并移除一条消息")

        # 1.构建锁
        lock_value = f"lock:{self._stream_name}:pop"

        # 2.构建分布式锁，如果分布式锁创建失败则返回 None
        lock_value = self._acquire_lock(lock_value)
        if not lock_value:
            return None, None

        try:
            # 3.从 redis 流中获取第一条消息
            messages = await self._redis.client.xrange(
                self._stream_name, "-", "+", count=1
            )
            if not messages:
                return None, None

            # 4.取出消息 id 和 消息
            message_id, message_data = messages[0]

            # 5.删除消息队列中的 message 数据
            await self._redis.client.xdel(self._stream_name, ids=message_id)

            return message_id, message_data.get("data")
        except Exception as e:
            logger.error(f"从消息队列{self._stream_name}中获取并移除消息失败：{e}")
            return None, None

    async def clear(self) -> None:
        """清空消息队列"""
        logger.debug(f"清空消息队列{self._stream_name}")
        await self._redis.client.xtrim(self._stream_name, maxlen=0)

    async def is_empty(self) -> bool:
        """判断消息队列是否为空"""
        return await self.size() == 0

    async def size(self) -> int:
        """获取消息队列中消息的数量"""
        return await self._redis.client.xlen(self._stream_name)

    async def delete_message(self, message_id: str) -> bool:
        """删除指定ID的消息"""
        try:
            await self._redis.client.xdel(self._stream_name, message_id)
            return True
        except Exception as e:
            return False
