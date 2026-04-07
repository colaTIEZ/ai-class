"""问题生成服务和节点单元测试

测试 question_generator 服务和 question_gen_node 的逻辑。
使用 mock 避免实际 LLM API 调用。
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from app.services.question_generator import (
    format_context,
    parse_llm_response,
    generate_question,
    SYSTEM_PROMPT,
    MULTIPLE_CHOICE_TEMPLATE,
    SHORT_ANSWER_TEMPLATE
)
from app.graph.nodes.question_gen import question_gen_node
from app.graph.state import SocraticState, QuestionSchema


class TestFormatContext:
    """测试上下文格式化函数"""
    
    def test_empty_chunks(self):
        """空 chunks 返回空字符串"""
        result = format_context([])
        assert result == ""
    
    def test_single_chunk(self):
        """单个 chunk 格式化正确"""
        chunks = [{"label": "Chapter 1", "chunk_text": "Introduction to Python."}]
        result = format_context(chunks)
        assert "[Chapter 1]" in result
        assert "Introduction to Python." in result
    
    def test_multiple_chunks(self):
        """多个 chunks 按顺序格式化"""
        chunks = [
            {"label": "Section 1", "chunk_text": "First section."},
            {"label": "Section 2", "chunk_text": "Second section."}
        ]
        result = format_context(chunks)
        assert "[Section 1]" in result
        assert "[Section 2]" in result
        assert "First section." in result
        assert "Second section." in result
    
    def test_missing_label(self):
        """缺少 label 使用默认值"""
        chunks = [{"chunk_text": "Some content."}]
        result = format_context(chunks)
        assert "[Section 1]" in result
        assert "Some content." in result


class TestParseLlmResponse:
    """测试 LLM 响应解析函数"""
    
    def test_valid_json(self):
        """有效 JSON 解析正确"""
        response = json.dumps({
            "question_text": "What is Python?",
            "options": ["A language", "A snake", "A game", "A movie"],
            "correct_answer": "A language"
        })
        
        result = parse_llm_response(response)
        
        assert result["question_text"] == "What is Python?"
        assert len(result["options"]) == 4
        assert result["correct_answer"] == "A language"
    
    def test_json_with_markdown(self):
        """带 markdown 代码块的 JSON 能正确解析"""
        response = '''```json
{
    "question_text": "What is 2+2?",
    "options": null,
    "correct_answer": "4"
}
```'''
        
        result = parse_llm_response(response)
        assert result["question_text"] == "What is 2+2?"
    
    def test_short_answer_format(self):
        """简答题格式（options 为 null）"""
        response = json.dumps({
            "question_text": "Explain Python.",
            "options": None,
            "correct_answer": "Python is a programming language."
        })
        
        result = parse_llm_response(response)
        assert result["options"] is None
    
    def test_missing_question_text(self):
        """缺少 question_text 抛出异常"""
        response = json.dumps({
            "options": ["A", "B"],
            "correct_answer": "A"
        })
        
        with pytest.raises(ValueError, match="Missing required field"):
            parse_llm_response(response)
            
    def test_insufficient_context_error(self):
        """处理 LLM 返回的显式错误"""
        response = json.dumps({
            "error": "INSUFFICIENT_CONTEXT"
        })
        with pytest.raises(ValueError, match="LLM reported insufficient context"):
            parse_llm_response(response)
            
    def test_robust_field_names(self):
        """处理不标准但含义正确的字段名 (如 question, answer, uppercase)"""
        response = json.dumps({
            "QUESTION": "Is this robust?",
            "OPTIONS": ["Yes", "No"],
            "ANSWER": "Yes"
        })
        result = parse_llm_response(response)
        assert result["question_text"] == "Is this robust?"
        assert result["options"] == ["Yes", "No"]
        assert result["correct_answer"] == "Yes"

    def test_invalid_json(self):
        """无效 JSON 抛出异常"""
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_llm_response("not valid json")


class TestGenerateQuestion:
    """测试问题生成函数（使用 mock）"""
    
    def test_empty_chunks_raises(self):
        """空 chunks 抛出 ValueError"""
        with pytest.raises(ValueError, match="No chunks provided"):
            generate_question([], "multiple_choice")
    
    def test_empty_context_raises(self):
        """空上下文抛出 ValueError"""
        chunks = [{"label": "test", "chunk_text": "   "}]  # 只有空白字符
        with pytest.raises(ValueError, match="Context is empty"):
            generate_question(chunks, "multiple_choice")
    
    @patch("app.services.question_generator.get_llm_client")
    def test_multiple_choice_uses_correct_template(self, mock_get_llm):
        """多选题使用正确的模板"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "question_text": "What is X?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A"
        })
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        chunks = [{"label": "Test", "chunk_text": "Content about X."}]
        result = generate_question(chunks, "multiple_choice")
        
        # 验证调用了 LLM
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]
        
        # 验证消息结构
        assert len(call_args) == 2  # System + Human
        assert "ONLY use information from the provided context" in call_args[0].content
        
        # 验证结果
        assert result["question_text"] == "What is X?"
        assert len(result["options"]) == 4
    
    @patch("app.services.question_generator.get_llm_client")
    def test_short_answer_uses_correct_template(self, mock_get_llm):
        """简答题使用正确的模板"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "question_text": "Explain X.",
            "options": None,
            "correct_answer": "X is..."
        })
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        chunks = [{"label": "Test", "chunk_text": "Content about X."}]
        result = generate_question(chunks, "short_answer")
        
        assert result["question_text"] == "Explain X."
        assert result["options"] is None


class TestQuestionGenNode:
    """测试 question_gen_node LangGraph 节点"""
    
    def test_skips_on_previous_error(self):
        """前序节点有错误时跳过生成"""
        state: SocraticState = {
            "selected_node_ids": ["node1"],
            "retrieved_chunks": [{"chunk_text": "test"}],
            "current_question": None,
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": "Previous error occurred"
        }
        
        result = question_gen_node(state)
        
        assert result["current_question"] is None
        assert result["trace_log"][0]["metadata"]["skipped"] is True
    
    def test_error_on_empty_chunks(self):
        """没有检索内容时报错"""
        state: SocraticState = {
            "selected_node_ids": ["node1"],
            "retrieved_chunks": [],
            "current_question": None,
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        
        result = question_gen_node(state)
        
        assert result["current_question"] is None
        assert "No content available" in result["error_message"]
    
    @patch("app.services.question_generator.generate_question")
    def test_successful_generation(self, mock_generate):
        """成功生成问题"""
        mock_question: QuestionSchema = {
            "question_text": "What is Python?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A"
        }
        mock_generate.return_value = mock_question
        
        state: SocraticState = {
            "selected_node_ids": ["node1"],
            "retrieved_chunks": [{"chunk_text": "Python is a language."}],
            "current_question": None,
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        
        result = question_gen_node(state)
        
        assert result["current_question"] == mock_question
        assert result["trace_log"][0]["metadata"]["success"] is True
        assert "error_message" not in result or result.get("error_message") is None
    
    @patch("app.services.question_generator.generate_question")
    def test_handles_generation_error(self, mock_generate):
        """处理生成错误"""
        mock_generate.side_effect = Exception("LLM API failed")
        
        state: SocraticState = {
            "selected_node_ids": ["node1"],
            "retrieved_chunks": [{"chunk_text": "Some content."}],
            "current_question": None,
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        
        result = question_gen_node(state)
        
        assert result["current_question"] is None
        assert "LLM API failed" in result["error_message"]
        assert result["trace_log"][0]["metadata"]["success"] is False
    
    def test_trace_log_contains_metadata(self):
        """追踪日志包含必要的元数据"""
        state: SocraticState = {
            "selected_node_ids": ["node1"],
            "retrieved_chunks": [],
            "current_question": None,
            "question_type": "short_answer",
            "trace_log": [{"node": "init", "timestamp": "2026-01-01", "metadata": {}}],
            "error_message": None
        }
        
        result = question_gen_node(state)
        
        # 验证新增了追踪日志
        assert len(result["trace_log"]) == 2
        new_entry = result["trace_log"][1]
        
        assert new_entry["node"] == "question_gen"
        assert "timestamp" in new_entry
        assert "metadata" in new_entry


class TestPromptTemplates:
    """测试提示模板"""
    
    def test_system_prompt_anti_hallucination(self):
        """系统提示包含反幻觉指令"""
        assert "ONLY use information from the provided context" in SYSTEM_PROMPT
        assert "DO NOT use any external knowledge" in SYSTEM_PROMPT
    
    def test_multiple_choice_template_format(self):
        """多选题模板格式正确"""
        assert "LEARNING MATERIAL:" in MULTIPLE_CHOICE_TEMPLATE
        assert "{context}" in MULTIPLE_CHOICE_TEMPLATE
        assert "4 options" in MULTIPLE_CHOICE_TEMPLATE
        assert "JSON" in MULTIPLE_CHOICE_TEMPLATE
    
    def test_short_answer_template_format(self):
        """简答题模板格式正确"""
        assert "LEARNING MATERIAL:" in SHORT_ANSWER_TEMPLATE
        assert "{context}" in SHORT_ANSWER_TEMPLATE
        assert '"options": null' in SHORT_ANSWER_TEMPLATE
