"""问题生成服务

使用外部 LLM API 基于检索内容生成测验问题。
严格遵循反幻觉原则：只使用提供的上下文生成问题。
"""

import json
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.llm_config import LLMConfig
from app.graph.nodes.llm_runtime import invoke_with_retry
from app.graph.prompts.question_gen_prompts import (
        QUESTION_GEN_SYSTEM_PROMPT,
        MULTIPLE_CHOICE_TEMPLATE,
        SHORT_ANSWER_TEMPLATE,
)
from app.graph.state import QuestionSchema


# 兼容现有测试命名
SYSTEM_PROMPT = QUESTION_GEN_SYSTEM_PROMPT


def get_llm_client() -> ChatOpenAI:
    """创建 LLM 客户端
    
    使用 pydantic-settings 配置的外部 API。
    支持 DeepSeek, GLM 等兼容 OpenAI API 的服务。
    
    Returns:
        ChatOpenAI: 配置好的 LLM 客户端
    """
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        model=settings.openai_model,
        temperature=LLMConfig.TEMPERATURE,
        timeout=LLMConfig.TIMEOUT_SECONDS,
    )


def format_context(retrieved_chunks: list[dict]) -> str:
    """格式化检索到的 chunks 为上下文字符串
    
    Args:
        retrieved_chunks: 检索到的文本块列表
        
    Returns:
        格式化的上下文字符串
    """
    if not retrieved_chunks:
        return ""
    
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        label = chunk.get("label", f"Section {i}")
        text = (chunk.get("chunk_text", "") or "").strip()
        if text:  # 只添加非空文本
            context_parts.append(f"[{label}]\n{text}")
    
    return "\n\n".join(context_parts)


def parse_llm_response(response_text: str) -> QuestionSchema:
    """解析 LLM 响应为 QuestionSchema
    
    Args:
        response_text: LLM 返回的 JSON 字符串
        
    Returns:
        解析后的 QuestionSchema
        
    Raises:
        ValueError: JSON 解析失败、格式不对、或上下文不足
    """
    # 清理可能的 markdown 代码块
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # 寻找第一个 { 和最后一个 }
        first_brace = -1
        last_brace = -1
        for i, line in enumerate(lines):
            if "{" in line and first_brace == -1:
                first_brace = i
            if "}" in line:
                last_brace = i
        
        if first_brace != -1 and last_brace != -1:
            cleaned = "\n".join(lines[first_brace:last_brace+1])
        else:
            # 备选方案：移除第一行和最后一行
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    # 再次清理，防止残留 markdown
    cleaned = cleaned.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # 记录原始文本以便调试，但限制长度
        preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
        raise ValueError(f"Failed to parse LLM response as JSON: {e}. Raw content: {preview}")
    
    # 检查 LLM 返回的显式错误（如 INSUFFICIENT_CONTEXT）
    if "error" in data:
        error_type = data["error"]
        if error_type == "INSUFFICIENT_CONTEXT":
            raise ValueError("LLM reported insufficient context to generate a question.")
        raise ValueError(f"LLM reported an error: {error_type}")

    # 兼容性处理：有些 LLM 可能返回大写或稍微不同的字段名
    # 我们映射到标准字段
    field_map = {
        "question_text": ["question_text", "question", "text"],
        "correct_answer": ["correct_answer", "answer", "correct"],
        "options": ["options", "choices"]
    }
    
    normalized_data = {}
    for standard_field, aliases in field_map.items():
        found = False
        for alias in aliases:
            # 检查原词、大写、标题化
            for variation in [alias, alias.upper(), alias.capitalize()]:
                if variation in data:
                    normalized_data[standard_field] = data[variation]
                    found = True
                    break
            if found: break
        
        if not found and standard_field != "options":
            required_zh = "问题文本" if standard_field == "question_text" else "正确答案"
            raise ValueError(f"Missing required field: {standard_field} ({required_zh})")

    return QuestionSchema(
        question_text=normalized_data["question_text"],
        options=normalized_data.get("options"),
        correct_answer=normalized_data["correct_answer"]
    )


def generate_question(
    retrieved_chunks: list[dict],
    question_type: Literal["multiple_choice", "short_answer"]
) -> QuestionSchema:
    """基于检索内容生成测验问题

    使用外部 LLM API 生成问题，严格限制只使用提供的上下文。

    Args:
        retrieved_chunks: 检索到的文本块列表
        question_type: 问题类型

    Returns:
        生成的问题

    Raises:
        ValueError: 如果 retrieved_chunks 为空或 LLM 响应无效
        Exception: LLM API 调用失败
    """
    if not retrieved_chunks:
        raise ValueError("No chunks provided for question generation")
    
    # 格式化上下文
    context = format_context(retrieved_chunks)
    
    if not context.strip():
        raise ValueError("Context is empty after formatting")
    
    # 选择模板
    if question_type == "multiple_choice":
        template = MULTIPLE_CHOICE_TEMPLATE
    else:
        template = SHORT_ANSWER_TEMPLATE
    
    # 构建消息
    user_message = template.format(context=context)
    
    # 调用 LLM
    llm = get_llm_client()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    def _invoke_question_llm():
        return llm.invoke(messages)

    response = invoke_with_retry(
        _invoke_question_llm,
        max_attempts=LLMConfig.MAX_RETRIES,
        base_delay_seconds=LLMConfig.RETRY_BASE_WAIT_SECONDS,
    )
    
    # 解析响应
    return parse_llm_response(response.content)
