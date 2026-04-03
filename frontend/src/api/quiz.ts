/**
 * Quiz API 客户端
 * 提供 Quiz 初始化和问题生成的 API 调用
 */

import type { ApiEnvelope } from '../types'

const API_BASE = '/api/v1'

/** 问题数据结构 */
export interface QuestionData {
  question_text: string
  options: string[] | null
  correct_answer: string
}

/** Quiz 初始化响应数据 */
export interface QuizInitData {
  question: QuestionData
  question_type: 'multiple_choice' | 'short_answer'
}

/** Quiz 初始化请求参数 */
export interface QuizInitRequest {
  selected_node_ids: string[]
  question_type?: 'multiple_choice' | 'short_answer'
}

/**
 * 初始化 Quiz 会话
 * 调用后端 LangGraph 流程生成测验问题
 *
 * @param request - Quiz 初始化请求
 * @returns 包含生成问题的响应
 */
export async function initQuiz(
  request: QuizInitRequest
): Promise<ApiEnvelope<QuizInitData>> {
  const response = await fetch(`${API_BASE}/quiz/init`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const errorMessage =
      errorData?.detail?.message || `API error: ${response.status}`
    throw new Error(errorMessage)
  }

  return response.json()
}
