"""问题生成服务

使用外部 LLM API 基于检索内容生成测验问题。
严格遵循反幻觉原则：只使用提供的上下文生成问题。
"""

import json
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.graph.state import QuestionSchema


# 系统提示模板 - 强调只使用提供的上下文
SYSTEM_PROMPT = """You are a quiz question generator for an educational system.

CRITICAL RULES:
1. You MUST ONLY use information from the provided context to generate questions.
2. DO NOT use any external knowledge or make up information.
3. If the context is insufficient to generate a question, respond with an error.
4. Questions must be directly answerable from the context.

Your task is to generate exactly ONE quiz question based on the provided learning material."""

# 多选题模板
MULTIPLE_CHOICE_TEMPLATE = """Based ONLY on the following learning material, generate ONE multiple choice question.

LEARNING MATERIAL:
{context}

REQUIREMENTS:
- Generate exactly 4 options (A, B, C, D)
- Only ONE option should be correct
- The correct answer MUST be directly stated or clearly implied in the material
- Incorrect options should be plausible but clearly wrong based on the material

RESPONSE FORMAT (JSON only, no markdown):
{{
  "question_text": "Your question here?",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "The correct option text"
}}"""

# 简答题模板
SHORT_ANSWER_TEMPLATE = """Based ONLY on the following learning material, generate ONE short answer question.

LEARNING MATERIAL:
{context}

REQUIREMENTS:
- The answer should be concise (1-2 sentences)
- The answer MUST be directly found in or derived from the material
- Do not ask for opinions or interpretations

RESPONSE FORMAT (JSON only, no markdown):
{{
  "question_text": "Your question here?",
  "options": null,
  "correct_answer": "The expected answer"
}}"""


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
        temperature=0.3,  # 低温度确保一致性
        timeout=10.0,  # 10秒超时（用户快速反馈）
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
        ValueError: JSON 解析失败或格式不正确
    """
    # 清理可能的 markdown 代码块
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # 移除第一行（```json）和最后一行（```）
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    
    # 验证必需字段
    required_fields = ["question_text", "correct_answer"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    return QuestionSchema(
        question_text=data["question_text"],
        options=data.get("options"),
        correct_answer=data["correct_answer"]
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
    
    response = llm.invoke(messages)
    
    # 解析响应
    return parse_llm_response(response.content)
