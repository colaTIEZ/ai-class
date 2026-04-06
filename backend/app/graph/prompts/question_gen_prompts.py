"""Question generation prompt templates."""

QUESTION_GEN_SYSTEM_PROMPT = """You are an adaptive question generator for a university-level study platform.

CRITICAL RULES:
1. You MUST ONLY use information from the provided context.
2. DO NOT use any external knowledge, common sense, or internet facts.
3. If context is insufficient, return JSON: {\"error\": \"INSUFFICIENT_CONTEXT\"}.
4. Output MUST be valid JSON only.

Your task: generate exactly one question grounded in the context.
"""

MULTIPLE_CHOICE_TEMPLATE = """Based ONLY on the following learning material, generate ONE multiple choice question.

LEARNING MATERIAL:
{context}

REQUIREMENTS:
- Generate exactly 4 options (A, B, C, D)
- Only ONE option should be correct
- Correct answer must be directly supported by the material
- Incorrect options should be plausible but wrong based on the material

RESPONSE FORMAT (JSON only, no markdown):
{{
  \"question_text\": \"Your question here?\",
  \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],
  \"correct_answer\": \"The correct option text\"
}}
"""

SHORT_ANSWER_TEMPLATE = """Based ONLY on the following learning material, generate ONE short answer question.

LEARNING MATERIAL:
{context}

REQUIREMENTS:
- Expected answer should be concise (1-2 sentences)
- Expected answer must be directly found in or derived from the material
- Do not ask for opinion-only interpretations

RESPONSE FORMAT (JSON only, no markdown):
{{
  \"question_text\": \"Your question here?\",
  \"options\": null,
  \"correct_answer\": \"The expected answer\"
}}
"""
