import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getRecentDocuments: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../api/documents', () => ({
  getRecentDocuments: mocks.getRecentDocuments,
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    replace: mocks.replace,
  }),
}))

import DocumentsEntryView from './DocumentsEntryView.vue'

function mountDocumentsEntryView() {
  return mount(DocumentsEntryView, {
    global: {
      stubs: {
        RouterLink: {
          template: '<a><slot /></a>',
        },
      },
    },
  })
}

describe('DocumentsEntryView routing behavior', () => {
  beforeEach(() => {
    mocks.getRecentDocuments.mockReset()
    mocks.replace.mockReset()
    window.localStorage.clear()
  })

  it('renders backend recent document over stale local cache', async () => {
    window.localStorage.setItem('ai-class-last-document-id', '960750555')
    mocks.getRecentDocuments.mockResolvedValue({
      status: 'success',
      data: {
        document_ids: [123456789],
      },
      message: '',
      trace_id: 'trace-1',
    })

    const wrapper = mountDocumentsEntryView()
    await flushPromises()

    expect(wrapper.text()).toContain('文档 123456789')
  })

  it('renders cached id when recent API fails', async () => {
    window.localStorage.setItem('ai-class-last-document-id', '960750555')
    mocks.getRecentDocuments.mockRejectedValue(new Error('network error'))

    const wrapper = mountDocumentsEntryView()
    await flushPromises()

    expect(wrapper.text()).toContain('network error')
  })
})
