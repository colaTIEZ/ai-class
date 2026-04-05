import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const submitAnswer = vi.fn()
const resetQuiz = vi.fn()
const storeState = reactive({
  isLoading: false,
  error: null as string | null,
  hasQuestion: true,
  questionType: 'multiple_choice' as const,
  currentQuestion: {
    question_text: 'What is 2 + 2?',
    options: ['3', '4', '5'],
    correct_answer: '4',
    current_node_id: 'node-a',
  },
  currentAnswer: '',
  currentHint: null as string | null,
  traceLog: [] as Array<{ node_name: string; metadata: Record<string, unknown> }>,
  traceId: 'trace-1',
  selectedNodeIds: ['node-a'],
  escapeHatchVisible: true,
  guardrailReason: 'stuck',
  needsReviewQueued: true,
  isStreaming: false,
  submitAnswer,
  resetQuiz,
  startQuiz: vi.fn(),
})

vi.mock('../stores/quiz', () => ({
  useQuizStore: () => storeState,
}))

import QuizView from './QuizView.vue'

function mountQuizView() {
  return mount(QuizView, {
    global: {
      stubs: {
        RouterLink: {
          template: '<a><slot /></a>',
        },
      },
    },
  })
}

beforeEach(() => {
  submitAnswer.mockClear()
  resetQuiz.mockClear()
  storeState.escapeHatchVisible = true
  storeState.guardrailReason = 'stuck'
  storeState.needsReviewQueued = true
  storeState.isStreaming = false
  storeState.error = null
})

describe('QuizView escape hatch', () => {
  it('renders escape hatch controls when the guardrail is active', () => {
    const wrapper = mountQuizView()

    expect(wrapper.text()).toContain('Guardrail Trigger: stuck')
    expect(wrapper.text()).toContain('Marked as Needs Review for follow-up.')
    expect(wrapper.text()).toContain('Show Answer')
    expect(wrapper.text()).toContain('Skip Question')
  })

  it('dispatches the show_answer and skip actions', async () => {
    const wrapper = mountQuizView()
    const buttons = wrapper.findAll('button')

    await buttons[1].trigger('click')
    expect(submitAnswer).toHaveBeenCalledWith('show_answer')

    await buttons[2].trigger('click')
    expect(submitAnswer).toHaveBeenCalledWith('skip')
  })

  it('renders trace pulses from the local store state', () => {
    storeState.traceLog = [
      { node_name: 'validate', metadata: { error_type: 'logic_gap' } },
      { node_name: 'sse', metadata: { first_byte_latency_ms: 42 } },
    ]

    const wrapper = mountQuizView()

    expect(wrapper.text()).toContain('Trace Log (2)')
    expect(wrapper.text()).toContain('validate')
    expect(wrapper.text()).toContain('logic_gap')
    expect(wrapper.text()).toContain('sse')
    expect(wrapper.text()).toContain('42')
  })
})
