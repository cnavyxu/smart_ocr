"""PDF票据处理相关的异常定义。

本模块定义票据处理流程中的统一异常类型。
"""

from __future__ import annotations


class PDFTicketProcessingError(Exception):
    """PDF票据处理过程中的统一异常类。
    
    用于封装PDF加载、票据检测、拆分等各环节的错误，
    便于上层调用者进行统一的异常处理。
    
    属性:
        message: 错误描述信息
        stage: 出错阶段（如 'loading', 'detection', 'splitting'）
        original_error: 原始异常对象（如果有）
    """
    
    def __init__(
        self,
        message: str,
        stage: str = "unknown",
        original_error: Exception | None = None,
    ):
        """初始化异常。
        
        参数:
            message: 错误描述信息
            stage: 出错阶段标识
            original_error: 原始异常对象
        """
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.original_error = original_error
    
    def __str__(self) -> str:
        """返回格式化的错误信息。"""
        base_msg = f"[{self.stage}] {self.message}"
        if self.original_error:
            base_msg += f" (原因: {str(self.original_error)})"
        return base_msg
