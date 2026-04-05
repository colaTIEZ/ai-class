import type { ApiEnvelope } from '../types'

const API_BASE = '/api/v1'
const USER_ID_STORAGE_KEY = 'ai-class-user-id'

export interface WrongAnswerQuestion {
  question_record_id: string
  question_id: string | null
  node_id: string
  question_text: string
  user_answer: string
  correct_answer: string
  error_type: string
  error_severity: number
  question_type: 'multiple_choice' | 'short_answer'
  attempted_at: string
  is_invalidated: boolean
}

export interface WrongAnswerNodeGroup {
  node_id: string
  node_label: string
  total_errors: number
  questions: WrongAnswerQuestion[]
}

export interface WrongAnswersData {
  by_node: WrongAnswerNodeGroup[]
  summary: {
    total_wrong_count: number
    total_nodes_with_errors: number
  }
}

function getClientUserId(): string {
  if (typeof window === 'undefined') {
    return 'anonymous'
  }

  const storedUserId = window.localStorage.getItem(USER_ID_STORAGE_KEY)
  if (storedUserId && storedUserId.trim()) {
    return storedUserId
  }

  const generatedUserId =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `user-${Date.now()}-${Math.random().toString(16).slice(2)}`

  window.localStorage.setItem(USER_ID_STORAGE_KEY, generatedUserId)
  return generatedUserId
}

export async function getWrongAnswers(
  nodeIdFilter?: string
): Promise<ApiEnvelope<WrongAnswersData>> {
  const url = new URL(`${API_BASE}/review/wrong-answers`, window.location.origin)
  if (nodeIdFilter && nodeIdFilter.trim()) {
    url.searchParams.set('node_id_filter', nodeIdFilter.trim())
  }

  const response = await fetch(url.toString(), {
    headers: {
      'X-User-ID': getClientUserId(),
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const errorMessage = errorData?.message || `API error: ${response.status}`
    throw new Error(errorMessage)
  }

  return response.json()
}
