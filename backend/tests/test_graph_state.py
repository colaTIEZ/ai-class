"""LangGraph State Schema 单元测试

验证 SocraticState TypedDict 结构正确性。
"""

import pytest
from typing import get_type_hints, get_origin, get_args
from datetime import datetime


class TestSocraticStateSchema:
    """SocraticState 状态模式测试"""

    def test_state_import(self):
        """验证 state 模块可正常导入"""
        from app.graph.state import SocraticState, QuestionSchema, TraceEntry
        assert SocraticState is not None
        assert QuestionSchema is not None
        assert TraceEntry is not None

    def test_state_fields_exist(self):
        """验证 SocraticState 包含所有必需字段"""
        from app.graph.state import SocraticState
        
        hints = get_type_hints(SocraticState)
        required_fields = [
            "selected_node_ids",
            "retrieved_chunks",
            "current_question",
            "question_type",
            "current_answer",
            "validation_result",
            "error_type",
            "current_hint",
            "conversation_history",
            "trace_log",
            "error_message"
        ]
        
        for field in required_fields:
            assert field in hints, f"Missing required field: {field}"

    def test_state_field_types(self):
        """验证 SocraticState 字段类型正确"""
        from app.graph.state import SocraticState
        
        hints = get_type_hints(SocraticState)
        
        # selected_node_ids should be list[str]
        assert get_origin(hints["selected_node_ids"]) == list
        
        # retrieved_chunks should be list[dict]
        assert get_origin(hints["retrieved_chunks"]) == list
        
        # question_type should be Literal
        from typing import Literal
        assert get_origin(hints["question_type"]) == Literal

    def test_question_schema_fields(self):
        """验证 QuestionSchema 包含所有必需字段"""
        from app.graph.state import QuestionSchema
        
        hints = get_type_hints(QuestionSchema)
        required_fields = ["question_text", "options", "correct_answer"]
        
        for field in required_fields:
            assert field in hints, f"Missing required field: {field}"

    def test_trace_entry_fields(self):
        """验证 TraceEntry 包含所有必需字段"""
        from app.graph.state import TraceEntry
        
        hints = get_type_hints(TraceEntry)
        required_fields = ["node", "timestamp", "metadata"]
        
        for field in required_fields:
            assert field in hints, f"Missing required field: {field}"

    def test_state_instantiation(self):
        """验证可以正确实例化 SocraticState"""
        from app.graph.state import SocraticState, QuestionSchema
        
        # 创建有效状态
        state: SocraticState = {
            "selected_node_ids": ["node_1", "node_2"],
            "retrieved_chunks": [
                {"node_id": "node_1", "chunk_text": "Sample text", "score": 0.95}
            ],
            "current_question": {
                "question_text": "What is X?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A"
            },
            "question_type": "multiple_choice",
            "trace_log": [
                {
                    "node": "init",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {"test": True}
                }
            ],
            "error_message": None
        }
        
        assert state["selected_node_ids"] == ["node_1", "node_2"]
        assert len(state["retrieved_chunks"]) == 1
        assert state["question_type"] == "multiple_choice"

    def test_state_partial_instantiation(self):
        """验证 SocraticState 支持部分实例化 (total=False)"""
        from app.graph.state import SocraticState
        
        # SocraticState 使用 total=False，允许部分字段
        partial_state: SocraticState = {
            "selected_node_ids": ["node_1"]
        }
        
        assert partial_state["selected_node_ids"] == ["node_1"]


class TestOrchestratorSchema:
    """Orchestrator 模块测试"""

    def test_orchestrator_import(self):
        """验证 orchestrator 模块可正常导入"""
        from app.graph.orchestrator import (
            build_quiz_graph,
            build_answer_feedback_graph,
            compile_graph,
            invoke_quiz_generation,
            invoke_answer_feedback,
            create_checkpointer
        )
        assert build_quiz_graph is not None
        assert build_answer_feedback_graph is not None
        assert compile_graph is not None
        assert invoke_quiz_generation is not None
        assert invoke_answer_feedback is not None

    def test_build_quiz_graph(self):
        """验证 StateGraph 构建正确"""
        from app.graph.orchestrator import build_quiz_graph
        
        workflow = build_quiz_graph()
        
        # 验证 workflow 已创建
        assert workflow is not None
        
        # 验证节点存在
        assert "retrieve" in workflow.nodes
        assert "question_gen" in workflow.nodes

    def test_build_answer_feedback_graph(self):
        """验证答题反馈图构建正确"""
        from app.graph.orchestrator import build_answer_feedback_graph

        workflow = build_answer_feedback_graph()
        assert workflow is not None
        assert "validate" in workflow.nodes
        assert "socratic_hint" in workflow.nodes

    def test_checkpointer_path(self):
        """验证 checkpointer 路径生成正确"""
        from app.graph.orchestrator import get_checkpointer_path
        
        path = get_checkpointer_path()
        assert "langgraph_checkpoint.db" in path


class TestGraphNodesImport:
    """Graph Nodes 导入测试"""

    def test_nodes_package_import(self):
        """验证 nodes 包可正常导入"""
        from app.graph.nodes import retrieve_node, question_gen_node, validate_answer_node, generate_hint_node
        assert retrieve_node is not None
        assert question_gen_node is not None
        assert validate_answer_node is not None
        assert generate_hint_node is not None

    def test_retrieve_node_signature(self):
        """验证 retrieve_node 函数签名正确"""
        from app.graph.nodes.retrieve import retrieve_node
        import inspect
        
        sig = inspect.signature(retrieve_node)
        params = list(sig.parameters.keys())
        
        assert "state" in params

    def test_question_gen_node_signature(self):
        """验证 question_gen_node 函数签名正确"""
        from app.graph.nodes.question_gen import question_gen_node
        import inspect
        
        sig = inspect.signature(question_gen_node)
        params = list(sig.parameters.keys())
        
        assert "state" in params
