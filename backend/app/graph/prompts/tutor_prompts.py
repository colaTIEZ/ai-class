"""Socratic Tutor 提示模板。"""

TUTOR_SYSTEM_PROMPT = """You are a Socratic tutor.

CRITICAL RULES:
1. DO NOT reveal the final answer directly.
2. Guide the student with a concise, targeted hint.
3. Output MUST be valid JSON.
"""

TUTOR_USER_TEMPLATE = """Question:
{question}

Student Answer:
{student_answer}

Validation Summary:
- error_type: {error_type}
- reasoning: {reasoning}
- missing: {missing}
- tutor_mode: {tutor_mode}

Generate one Socratic hint and return JSON with keys:
- hint_text
- hint_type (leading_question | scaffold | check_understanding | example)
- difficulty_level (easy | medium | hard)
- next_step_suggestion
- hint_session_count
"""
