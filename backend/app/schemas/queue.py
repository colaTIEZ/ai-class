"""Queue 模块数据模型 - Pydantic 定义 API 数据结构"""

from pydantic import BaseModel, Field
from typing import Optional

class QueueItemData(BaseModel):
    """上传任务队列项数据字段"""
    job_id: str = Field(description="UUID 的处理任务ID")
    status: str = Field(description="任务处理状态", examples=["queued", "duplicate"])
    position: int = Field(description="当前排队名次")
    duplicated: bool = Field(default=False, description="是否命中重复文件")
    existing_document_id: Optional[int] = Field(default=None, description="命中重复时可复用的文档ID")

class QueueResponse(BaseModel):
    """标准上传队列响应协议封套"""
    status: str = Field(default="success", description="请求主状态")
    data: QueueItemData = Field(description="任务数据")
    message: str = Field(default="File accepted and queued for processing", description="系统提示信息")
    trace_id: str = Field(default="", description="调链路跟踪ID")
