import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useQuizStore } from './quiz'

const { submitAnswerStream, initQuiz } = vi.hoisted(() => ({
  submitAnswerStream: vi.fn(),
  initQuiz: vi.fn(),
}))

vi.mock('../api/quiz', () => ({
  initQuiz,
  submitAnswerStream,
}))

describe('quiz store escape hatch payload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    submitAnswerStream.mockReset()
    initQuiz.mockReset()
  })

  it('sends current_node_id from the current question', async () => {
    const store = useQuizStore()
    store.currentQuestion = {
      question_text: 'What is 2 + 2?',
      options: ['3', '4'],
      correct_answer: '4',
      current_node_id: 'node-42',
    }
    store.currentAnswer = '4'
    store.questionType = 'short_answer'

    submitAnswerStream.mockImplementation(async (request) => {
      expect(request.current_node_id).toBe('node-42')
      expect(request.action).toBe('skip')
    })

    await store.submitAnswer('skip')

    expect(submitAnswerStream).toHaveBeenCalledTimes(1)
  })
})
