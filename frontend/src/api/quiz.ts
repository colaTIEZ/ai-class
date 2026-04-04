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

export interface AnswerSubmitRequest {
  selected_node_ids: string[]
  question_type: 'multiple_choice' | 'short_answer'
  current_question: QuestionData
  current_answer: string
}

export interface StreamEvent {
  type: 'content' | 'trace' | 'error'
  data: Record<string, unknown>
  trace_id: string
  timestamp: string
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

export async function submitAnswerStream(
  request: AnswerSubmitRequest,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok || !response.body) {
    throw new Error(`API error: ${response.status}`)
  }
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    throw new Error(`Invalid stream content-type: ${contentType || 'unknown'}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const flushBuffer = (input: string) => {
    const blocks = input.split(/\r?\n\r?\n/)
    const remainder = blocks.pop() ?? ''
    for (const block of blocks) {
      const lines = block.split(/\r?\n/)
      const dataLines = lines.filter((line) => line.startsWith('data:'))
      if (!dataLines.length) continue
      const jsonPayload = dataLines
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (!jsonPayload) continue
      try {
        onEvent(JSON.parse(jsonPayload) as StreamEvent)
      } catch {
        continue
      }
    }
    return remainder
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      buffer = flushBuffer(buffer)
      break
    }
    buffer += decoder.decode(value, { stream: true })
    buffer = flushBuffer(buffer)
  }
}
