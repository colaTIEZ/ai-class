import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getWrongAnswers: vi.fn(),
  getChapterMastery: vi.fn(),
  invalidateQuestionRecord: vi.fn(),
  push: vi.fn(),
  clearSelection: vi.fn(),
  toggleNodeSelection: vi.fn(),
}))

vi.mock('../api/review', () => ({
  getWrongAnswers: mocks.getWrongAnswers,
  getChapterMastery: mocks.getChapterMastery,
  invalidateQuestionRecord: mocks.invalidateQuestionRecord,
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock('../stores/quiz', () => ({
  useQuizStore: () => ({
    clearSelection: mocks.clearSelection,
    toggleNodeSelection: mocks.toggleNodeSelection,
  }),
}))

import ReviewPage from './ReviewPage.vue'

function mountReviewPage() {
  return mount(ReviewPage, {
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
  mocks.getWrongAnswers.mockReset()
  mocks.getChapterMastery.mockReset()
  mocks.invalidateQuestionRecord.mockReset()
  mocks.push.mockReset()
  mocks.clearSelection.mockReset()
  mocks.toggleNodeSelection.mockReset()
  window.localStorage.clear()
})

describe('ReviewPage', () => {
  it('renders grouped wrong answers and filters by node', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 2,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'What is f\'(x)?',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
              {
                question_record_id: 'q-2',
                question_id: 'question-2',
                node_id: 'node-a',
                question_text: 'What is 2 + 2?',
                user_answer: '5',
                correct_answer: '4',
                error_type: 'logic_gap',
                error_severity: 1,
                question_type: 'multiple_choice',
                attempted_at: '2026-04-05T11:00:00Z',
                is_invalidated: false,
              },
            ],
          },
          {
            node_id: 'node-b',
            node_label: 'Integral basics',
            total_errors: 1,
            questions: [
              {
                question_record_id: 'q-3',
                question_id: 'question-3',
                node_id: 'node-b',
                question_text: 'What is ∫x dx?',
                user_answer: 'x',
                correct_answer: 'x^2/2 + C',
                error_type: 'incomplete',
                error_severity: 1,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T12:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 3,
          total_nodes_with_errors: 2,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [
          {
            parent_id: 'chapter-1',
            parent_label: 'Chapter 1',
            attempted_count: 3,
            correct_count: 2,
            mastery_score: 2 / 3,
          },
        ],
        summary: {
          total_parents: 1,
          total_attempted: 3,
          total_correct: 2,
          overall_mastery_score: 2 / 3,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    expect(wrapper.text()).toContain('错题回顾')
    expect(wrapper.text()).toContain('Derivative basics')
    expect(wrapper.text()).toContain('Integral basics')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('Chapter 1')
    expect(wrapper.text()).toContain('67%')

    const nodeButtons = wrapper.findAll('button')
    await nodeButtons[1].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Derivative basics')
    expect(wrapper.text()).not.toContain('Integral basics')
    expect(wrapper.text()).toContain('What is f\'(x)?')
  })

  it('sends the selected node back to quiz', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 1,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'What is f\'(x)?',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 1,
          total_nodes_with_errors: 1,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [],
        summary: {
          total_parents: 0,
          total_attempted: 0,
          total_correct: 0,
          overall_mastery_score: 0,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()

    await wrapper.find('.retry-btn').trigger('click')

    expect(mocks.clearSelection).toHaveBeenCalled()
    expect(mocks.toggleNodeSelection).toHaveBeenCalledWith('node-a', true)
    expect(mocks.push).toHaveBeenCalledWith('/quiz')
  })

  it('shows fallback when mastery payload is empty', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [],
        summary: {
          total_wrong_count: 0,
          total_nodes_with_errors: 0,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [],
        summary: {
          total_parents: 0,
          total_attempted: 0,
          total_correct: 0,
          overall_mastery_score: 0,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Mastery snapshot unavailable yet')
  })

  it('invalidates one question and prunes it from UI', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 2,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'What is f\'(x)?',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
              {
                question_record_id: 'q-2',
                question_id: 'question-2',
                node_id: 'node-a',
                question_text: 'What is 2 + 2?',
                user_answer: '5',
                correct_answer: '4',
                error_type: 'logic_gap',
                error_severity: 1,
                question_type: 'multiple_choice',
                attempted_at: '2026-04-05T11:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 2,
          total_nodes_with_errors: 1,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [],
        summary: {
          total_parents: 0,
          total_attempted: 0,
          total_correct: 0,
          overall_mastery_score: 0,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })
    mocks.invalidateQuestionRecord.mockResolvedValue({
      status: 'success',
      data: {
        question_record_id: 'q-1',
        found: true,
        updated: true,
        already_invalidated: false,
        invalidated_at: '2026-04-06T12:00:00Z',
      },
      message: '',
      trace_id: 'trace-3',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('What is f\'(x)?')
    expect(wrapper.text()).toContain('What is 2 + 2?')
    expect(wrapper.text()).toContain('2')

    const reportButtons = wrapper.findAll('button.report-ai-error')
    expect(reportButtons.length).toBe(2)
    await reportButtons[0].trigger('click')
    await flushPromises()

    expect(mocks.invalidateQuestionRecord).toHaveBeenCalledWith({
      question_record_id: 'q-1',
      reason: 'user_reported_ai_error',
    })
    expect(wrapper.text()).not.toContain('What is f\'(x)?')
    expect(wrapper.text()).toContain('What is 2 + 2?')
    expect(wrapper.text()).toContain('1')
  })

  it('shows empty-state fallback when invalidation removes the last question', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 1,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'Only wrong question',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 1,
          total_nodes_with_errors: 1,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [],
        summary: {
          total_parents: 0,
          total_attempted: 0,
          total_correct: 0,
          overall_mastery_score: 0,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })
    mocks.invalidateQuestionRecord.mockResolvedValue({
      status: 'success',
      data: {
        question_record_id: 'q-1',
        found: true,
        updated: true,
        already_invalidated: false,
        invalidated_at: '2026-04-06T12:00:00Z',
      },
      message: '',
      trace_id: 'trace-3',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()

    const reportButtons = wrapper.findAll('button.report-ai-error')
    expect(reportButtons.length).toBe(1)
    await reportButtons[0].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('还没有错题记录')
  })

  it('refreshes mastery snapshot after successful invalidation', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 1,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'Only wrong question',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 1,
          total_nodes_with_errors: 1,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })

    mocks.getChapterMastery
      .mockResolvedValueOnce({
        status: 'success',
        data: {
          by_parent: [
            {
              parent_id: 'chapter-1',
              parent_label: 'Chapter 1',
              attempted_count: 1,
              correct_count: 1,
              mastery_score: 1,
            },
          ],
          summary: {
            total_parents: 1,
            total_attempted: 1,
            total_correct: 1,
            overall_mastery_score: 1,
          },
        },
        message: '',
        trace_id: 'trace-2',
      })
      .mockResolvedValueOnce({
        status: 'success',
        data: {
          by_parent: [],
          summary: {
            total_parents: 0,
            total_attempted: 0,
            total_correct: 0,
            overall_mastery_score: 0,
          },
        },
        message: '',
        trace_id: 'trace-3',
      })

    mocks.invalidateQuestionRecord.mockResolvedValue({
      status: 'success',
      data: {
        question_record_id: 'q-1',
        found: true,
        updated: true,
        already_invalidated: false,
        invalidated_at: '2026-04-06T12:00:00Z',
      },
      message: '',
      trace_id: 'trace-4',
    })

    const wrapper = mountReviewPage()
    await flushPromises()

    expect(wrapper.text()).toContain('100%')

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()

    await wrapper.findAll('button.report-ai-error')[0].trigger('click')
    await flushPromises()

    expect(mocks.getChapterMastery).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('0%')
  })

  it('shows report error feedback when invalidation request fails', async () => {
    mocks.getWrongAnswers.mockResolvedValue({
      status: 'success',
      data: {
        by_node: [
          {
            node_id: 'node-a',
            node_label: 'Derivative basics',
            total_errors: 1,
            questions: [
              {
                question_record_id: 'q-1',
                question_id: 'question-1',
                node_id: 'node-a',
                question_text: 'Only wrong question',
                user_answer: 'x',
                correct_answer: '2x',
                error_type: 'calculation',
                error_severity: 2,
                question_type: 'short_answer',
                attempted_at: '2026-04-05T10:00:00Z',
                is_invalidated: false,
              },
            ],
          },
        ],
        summary: {
          total_wrong_count: 1,
          total_nodes_with_errors: 1,
        },
      },
      message: '',
      trace_id: 'trace-1',
    })
    mocks.getChapterMastery.mockResolvedValue({
      status: 'success',
      data: {
        by_parent: [],
        summary: {
          total_parents: 0,
          total_attempted: 0,
          total_correct: 0,
          overall_mastery_score: 0,
        },
      },
      message: '',
      trace_id: 'trace-2',
    })
    mocks.invalidateQuestionRecord.mockRejectedValue(new Error('network error'))

    const wrapper = mountReviewPage()
    await flushPromises()

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button.report-ai-error')[0].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('network error')
    expect(wrapper.text()).toContain('Only wrong question')
  })
})
