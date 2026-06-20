import io
import logging
from docker.models.resource import Model
import httpx
import asyncio
import socket
import uuid
import docker

from typing import Optional, Self, BinaryIO
from async_lru import alru_cache

from app.domain.external.browser import Browser
from app.domain.external.sandbox import Sandbox
from app.domain.models.tool_result import ToolResult
from app.infrastructure.external.browser.playwright_browser import PlaywrightBrowser
from app.infrastructure.external.sandbox.dto.file import FileCheckRequest, FileDeleteRequest, FileFindRequest, FileReadRequest, FileReplaceRequest, FileSearchRequest, FileWriteRequest
from app.infrastructure.external.sandbox.dto.shell import ShellExecuteReqeust, ShellKillRequest, ShellReadRequest, ShellWaitRequest, ShellWriteRequest
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

class DockerSandbox(Sandbox):
    """基于 Docker 的沙箱服务"""

    def __init__(
        self,
        ip: Optional[str] = None,
        container_name: Optional[str] = None
    ) -> None:
        """构造函数,完成 Dcoker 沙箱扩展的创建"""
        self.client = httpx.AsyncClient(timeout=600)
        self._ip = ip
        self._container_name = container_name
        self._base_url = f"http://{ip}:8080"
        self._vnc_url = f"ws://{ip}:5901"
        self._cdp_url = f"http://{ip}:9222"

    @property
    def id(self) -> str:
        """获取沙箱的唯一ID,使用容器名字作为唯一ID"""
        if not self._container_name:
            return "nano-manus-sandbox"
        return self._container_name

    @property
    def vnc_url(self) -> str:
        return self._vnc_url
    
    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @classmethod
    @alru_cache(maxsize=128, typed=True)
    async def _resolve_hostname_to_ip(cls, hostname: str) -> Optional[str]:
        """将 Docker 容器主机/地址转换为 ipv4 格式数据"""
        try:
            try:
                # 1.首先解析传递的 hostname 是不是 ip
                socket.inet_pton(socket.AF_INET, hostname)
                return hostname
            except OSError:
                pass

            # 2.使用 socket 获取地址信息
            addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_INET)

            # 3.判断地址信息是否存在，如果存在则返回第一个 Ipv4 地址
            if addr_info and len(addr_info) > 0:
                return addr_info[0][4][0]

            return None
        except Exception as e:
            logger.error(f"解析 Docker 容器主机地址 {hostname} 失败，{str(e)}")
            return None
    
    @classmethod
    def _get_container_ip(cls, container: Model) -> str:
        """根据传递的容器获取 ip 信息"""
        # 1.获取 inspect 网络设置
        network_settings = container.attrs["NetworkSettings"]
        ip_address = network_settings["IPAddress"]

        # 2.判断容器是否存在 ip,如果不存在则从 networks 中获取
        if not ip_address and "Networks" in network_settings:
            networks = network_settings["Networks"]
            # 3.循环遍历每一项网络配置
            for network_name, network_config in networks.items():
                if "IPAddress" in network_config and network_config["IPAddress"]:
                    ip_address = network_config["IPAddress"]
                    break
        
        return ip_address

    @classmethod
    def _create_task(cls) -> Self:
        """创建沙箱容器的异步任务"""
        # 1.获取系统配置信息
        settings: Settings = get_settings()

        # 2.构建容器的名字
        image = settings.sandbox_image
        name_prefix = settings.sandbox_name_prefix
        container_name = f"{name_prefix}-{str(uuid.uuid4())[:8]}"

        try:
            # 3.创建一个 docker 客户端
            docker_client = docker.from_env()

            # 4.预配置容器信息
            container_config = {
                "image": image,
                "name": container_name,
                "detach": True,
                "remove": True,
                "environment": {
                    "SERVICE_TIMEOUT_MINUTES": settings.sandbox_ttl_minutes,
                    "CHROME_ARGS": settings.sandbox_chrome_args,
                    "HTTPS_PROXY": settings.sandbox_https_proxy,
                    "HTTP_PROXY": settings.sandbox_http_proxy,
                    "NO_PROXY": settings.sandbox_no_proxy,
                }
            }

            # 5.判断是否传递了网络
            if settings.sandbox_network:
                container_config["network"] = settings.sandbox_network
            
            # 6.调用 docker 客户端容器运行参数创建沙箱
            container = docker_client.containers.run(**container_config)

            # 7.重载并刷新容器信息
            container.reload()
            ip = cls._get_container_ip(container)

            return DockerSandbox(ip=ip, container_name=container_name)

        except Exception as e:
            logger.error(f"创建 Docker 沙箱容器失败: {str(e)}")
            raise Exception(f"创建 Docker 沙箱容器失败: {str(e)}")

    @classmethod
    async def create(cls) -> Self:
        """类方法，创建沙箱容器实例"""
        # 1.获取系统配置信息
        settings: Settings = get_settings()

        # 2.判断是否使用现成的沙箱
        if settings.sandbox_address:
            # 3.将沙箱主机/地址解析成 ip
            ip = await cls._resolve_hostname_to_ip(settings.sandbox_address)
            return DockerSandbox(ip=ip)
        
        # 4.使用子线程创建一个容器后返回
        return await asyncio.to_thead(cls._create_task)

    async def destroy(self) -> bool:
        """
        销毁当前的 DockerSandbox 实例
        """
        try:
            # 1.关闭 httpx 客户端
            if self.client:
                await self.client.aclose()

            # 2.关闭并移除容器
            if self._container_name:
                docker_client = docker.from_env()
                docker_client.containers.get(self._container_name).remove(force=True)
            return True
        except Exception as e:
            logger.error(f"销毁当前 Docker 沙箱[{self._container_name}]失败：{str(e)}")
            return False

    @classmethod
    @alru_cache(maxsize=128, typed=True)
    async def get(cls, id: str) -> Self:
        """
        根据传递的 id 获取沙箱实例
        """
        # 1.先获取系统配置并判断是否直连沙箱
        settings: Settings = get_settings()
        if settings.sandbox_address:
            ip = cls._resolve_hostname_to_ip(settings.sandbox_address)
            return DockerSandbox(ip=ip, container_name=id)
        
        # 2.创建 docker 客户端并根据容器名字获取容器
        docker_client = docker.from_env()
        container = docker_client.containers.get(id)

        # 3.获取容器的 ip 地址
        ip = cls._get_container_ip(container)
        return DockerSandbox(ip=ip, container_name=id)


    async def get_browser(self) -> Browser:
        """
        获取沙箱中的浏览器实例
        """
        return PlaywrightBrowser(cdp_url=self.cdp_url)


    async def ensure_sandbox(self) -> None:
        """
        确保沙箱一定存在/服务全部都开启了才能执行后续步骤
        """
        # 1.定义最大重试次数 + 重试隔离
        max_retries = 30
        retry_interval = 2

        # 2.循环请求来获取 supervisor 状态并判断服务是否正常
        for attemp in range(max_retries):
            try:
                # 3.调用 client 客户端向沙箱发起 api 请求获取状态
                response = await self.client.get(f"{self._base_url}/api/supervisor/status")
                response.raise_for_status()

                # 4.将响应结果转换为 ToolResult
                tool_result = ToolResult.from_sandbox( **response.json())

                # 5.判断是否执行成功
                if not tool_result.success:
                    logger.warning(f"Supervisor 进程状态监测失效：{tool_result.message}")
                    await asyncio.sleep(retry_interval)
                
                # 6.读取 services 数据并判断
                services = tool_result.data or []
                if not services:
                    logger.warning("Supervisor 进程中没有发现任何服务")
                    await asyncio.sleep(retry_interval)
                    continue
                    
                # 7.循环遍历所有的服务并判断是否全部正常运行
                all_running = True
                non_running_service = []
                for service in services:
                    service_name = service.get("name", "unknown")
                    state_name = service.get("statename", "")

                    # 8.判断 state_name 是不是 RUNNING
                    if state_name != "RUNNING":
                        all_running = False
                        non_running_service.append(f"{service_name}({state_name})")

                # 判断是否所有服务都启动了
                if all_running:
                    logger.info("Sandbox Supervisor 所有进程服务运行正常")
                    return
                else:
                    logger.info(f"正在等待 Sandbox Supervisor 进程服务运行，还没成功运行服务：{non_running_service}")
                    await asyncio.sleep(retry_interval)

            except Exception as e:
                logger.warning(f"无法确认 Sandbox Supervisor 进程状态：{str(e)}")
                await asyncio.sleep(retry_interval)
        
        # 经过 max_retries 次检测后还无法确认，则抛出异常
        logger.error(f"在经过 {max_retries} 次尝试后仍无法确认 Sandbox Supervisor 状态信息")
        raise Exception(msg=f"在经过 {max_retries} 次尝试后仍无法确认 Sandbox Supervisor 状态信息")

    
    async def read_file(
        self,
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        sudo: bool = None,
        max_length: int = 10000
    ) -> ToolResult:
        """
        读取沙箱中指定路径的文件内容
        """
        response = await self.client.post(
            url=f"{self._base_url}/api/file/read-file",
            json=FileReadRequest(
                filepath=filepath,
                start_line=start_line,
                end_line=end_line,
                sudo=sudo,
                max_length=max_length,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def write_file(self, filepath: str, content: str, append: Optional[bool] = False, leading_newline: Optional[bool] = False, trailing_newline: Optional[bool] = False, sudo: Optional[bool] = False) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/file/write-file",
            json=FileWriteRequest(
                filepath=filepath,
                content=content,
                append=append,
                leading_newline=leading_newline,
                trailing_newline=trailing_newline,
                sudo=sudo
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def replace_in_file(self, filepath: str, old_str: str, new_str: str, sudo: Optional[bool] = False) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/file/replace-in-file",
            json=FileReplaceRequest(
                filepath=filepath,
                old_str=old_str,
                new_str=new_str,
                sudo=sudo,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def search_in_file(self, filepath: str, regex: str, sudo: Optional[bool] = False) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/file/search-in-file",
            json=FileSearchRequest(
                filepath=filepath,
                regex=regex,
                sudo=sudo,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def find_files(self, dir_path: str, glob_pattern: str) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/file/find-files",
            json=FileFindRequest(
                dir_path=dir,
                glob_pattern=glob_pattern,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def list_files(self, dir_path: str) -> ToolResult:
        """
        传递目录，列出沙箱指定目录下的所有文件
        """
        return await self.find_files(dir_path=dir_path, glob_pattern="*")

    async def check_file_exists(self, filepath: str) -> ToolResult:
        """
        传递指定路径检查沙箱中指定文件是否存在
        """
        response = await self.client.post(
            url=f"{self._base_url}/api/file/check-file-exists",
            json=FileCheckRequest(
                filepath=filepath,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def delete_file(self, filepath: str) -> ToolResult:
        """
        传递路径，删除指定文件
        """
        response = await self.client.post(
            url=f"{self._base_url}/api/file/delete-file",
            json=FileDeleteRequest(
                filepath=filepath,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())
        
    async def upload_file(self, file_data: BinaryIO, filepath: str, filename: Optional[str] = None) -> ToolResult:
        """
        将文件上传到沙箱指定位置
        """
        # 1.预配置上传数据
        files = {"file": (filename or "upload", file_data, "application/octet-stream")}
        data = {"filepath": filepath}

        response = await self.client.post(
            url=f"{self._base_url}/api/file/upload-file",
            files=files,
            data=data,
            timeout=30.0
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def download_file(self, filepath: str) -> BinaryIO:
        """
        从沙箱中下载文件
        """
        response = await self.client.get(
            url=f"{self._base_url}/api/file/download-file",
            params={"filepath": filepath},
            timeout=20.0
        )
        response.raise_for_status()

        raw_bytes: bytes = await response.read()
        return io.BytesIO(raw_bytes)

    async def exec_command(self, session_id: str, exec_dir: str, command: str) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/shell/exec-command",
            json=ShellExecuteReqeust(
                session_id=session_id,
                exec_dir=exec_dir,
                command=command,
            ).model_dump(mode="json", exclude_none=True)
        )
        
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def read_shell_output(self, session_id: str, console: bool = False) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/shell/read-shell-output",
            json=ShellReadRequest(
                session_id=session_id,
                console=console,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())
    
    async def wait_process(self, session_id: str, seconds: Optional[int] = None) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/shell/wait-process",
            json=ShellWaitRequest(
                session_id=session_id,
                seconds=seconds,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())

    async def write_shell_input(self, session_id: str, input_text: str, press_enter: bool = True) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/shell/write-shell-input",
            json=ShellWriteRequest(
                session_id=session_id,
                input_text=input_text,
                press_enter=press_enter,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())
    

    async def kill_process(self, session_id: str) -> ToolResult:
        
        response = await self.client.post(
            url=f"{self._base_url}/api/shell/kill-process",
            json=ShellKillRequest(
                session_id=session_id,
            ).model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

        return ToolResult.from_sandbox(**response.json())
    
    
