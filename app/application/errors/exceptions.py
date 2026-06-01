from typing import Any

class AppException(RuntimeError):
    """
    基础应用异常类，继承自 RuntimeError
    """

    def __init__(
        self,
        code: int = 400,
        status_code: int = 400,
        msg: str = "",
        data: Any = None,
    ) -> None:
        self.code = (code,)
        self.status_code = status_code
        self.msg = msg
        self.data = data
        super().__init__()


class BadRequestError(AppException):
    """
    客户端请求错误，请检查后重试
    """

    def __init__(self, msg: str = "客户端请求错误，请检查后重试") -> None:
        super().__init__(status_code=400, code=400, msg=msg)


class NotFoundError(AppException):
    """
    资源未找到
    """

    def __init__(self, msg: str = "资源未找到,请核实后重试") -> None:
        super().__init__(status_code=404, code=404, msg=msg)


class ValidationError(AppException):
    """
    数据验证错误
    """

    def __init__(self, msg: str = "请求参数数据校验错误，请检查后重试") -> None:
        super().__init__(status_code=422, code=422, msg=msg)


class TooManyRequestError(AppException):
    """
    请求过多，请稍后重试
    """

    def __init__(self, msg: str = "请求过多，请稍后重试") -> None:
        super().__init__(status_code=429, code=429, msg=msg)


class ServerRequestError(AppException):
    """
    服务器内部错误
    """

    def __init__(self, msg: str = "服务器内部错误,请稍后重试") -> None:
        super().__init__(status_code=500, code=500, msg=msg)
