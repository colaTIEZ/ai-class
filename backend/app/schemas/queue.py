"""Queue 模块数据模型 - Pydantic 定义 API 数据结构"""

from pydantic import BaseModel, Field
from typing import Optional

class QueueItemData(BaseModel):
    """上传任务队列项数据字段"""
    job_id: str = Field(description="UUID 的处理任务ID")
    status: str = Field(description="任务处理状态", examples=["queued"])
    position: int = Field(description="当前排队名次")

class QueueResponse(BaseModel):
    """标准上传队列响应协议封套"""
    status: str = Field(default="success", description="请求主状态")
    data: QueueItemData = Field(description="任务数据")
    message: str = Field(default="File accepted and queued for processing", description="系统提示信息")
    trace_id: str = Field(default="", description="调链路跟踪ID")
