import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getDocumentTree: vi.fn(),
  getChapterMastery: vi.fn(),
  push: vi.fn(),
  routeId: 'abc',
  setActiveDocument: vi.fn(),
  hasSelection: false,
}))

vi.mock('../api/documents', () => ({
  getDocumentTree: mocks.getDocumentTree,
}))

vi.mock('../api/review', () => ({
  getChapterMastery: mocks.getChapterMastery,
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: mocks.routeId },
  }),
  useRouter: () => ({
    push: mocks.push,
  }),
}))

vi.mock('../stores/quiz', () => ({
  useQuizStore: () => ({
    hasSelection: mocks.hasSelection,
    setActiveDocument: mocks.setActiveDocument,
    toggleNodeSelection: vi.fn(),
  }),
}))

import DocumentView from './DocumentView.vue'

function mountDocumentView() {
  return mount(DocumentView, {
    global: {
      stubs: {
        KnowledgeGraph: {
          template: '<div>mock-graph</div>',
        },
        RouterLink: {
          template: '<a><slot /></a>',
        },
      },
    },
  })
}

describe('DocumentView route guards', () => {
  beforeEach(() => {
    mocks.getDocumentTree.mockReset()
    mocks.getChapterMastery.mockReset()
    mocks.push.mockReset()
    mocks.setActiveDocument.mockReset()
    mocks.routeId = 'abc'
    mocks.hasSelection = false
  })

  it('renders explicit error for invalid route id and avoids API calls', async () => {
    const wrapper = mountDocumentView()
    await flushPromises()

    expect(wrapper.text()).toContain('文档 ID 无效，请从上传页重新进入。')
    expect(mocks.setActiveDocument).not.toHaveBeenCalled()
    expect(mocks.getDocumentTree).not.toHaveBeenCalled()
  })
})
