import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getWrongAnswers: vi.fn(),
  push: vi.fn(),
  clearSelection: vi.fn(),
  toggleNodeSelection: vi.fn(),
}))

vi.mock('../api/review', () => ({
  getWrongAnswers: mocks.getWrongAnswers,
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

    const wrapper = mountReviewPage()
    await flushPromises()

    expect(wrapper.text()).toContain('按知识点回看错题')
    expect(wrapper.text()).toContain('Derivative basics')
    expect(wrapper.text()).toContain('Integral basics')
    expect(wrapper.text()).toContain('3')

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

    const wrapper = mountReviewPage()
    await flushPromises()

    await wrapper.findAll('button').at(1)?.trigger('click')
    await flushPromises()

    await wrapper.find('button.rounded-xl').trigger('click')

    expect(mocks.clearSelection).toHaveBeenCalled()
    expect(mocks.toggleNodeSelection).toHaveBeenCalledWith('node-a', true)
    expect(mocks.push).toHaveBeenCalledWith('/quiz')
  })
})
