import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  graphCtor: vi.fn(),
  toggleNodeSelection: vi.fn(),
}))

vi.mock('@antv/g6', () => ({
  Graph: class MockGraph {
    constructor(...args: unknown[]) {
      return mocks.graphCtor(...args)
    }
  },
}))

vi.mock('../../stores/quiz', () => ({
  useQuizStore: () => ({
    selectedNodeIds: [],
    toggleNodeSelection: mocks.toggleNodeSelection,
  }),
}))

import KnowledgeGraph from './KnowledgeGraph.vue'

const validTreeData = {
  document_id: 1,
  nodes: [
    {
      node_id: 'n1',
      label: 'Node 1',
      parent_id: null,
      content_summary: 'summary',
    },
  ],
  total_nodes: 1,
}

describe('KnowledgeGraph fail-safe rendering', () => {
  beforeEach(() => {
    mocks.graphCtor.mockReset()
    mocks.toggleNodeSelection.mockReset()
    mocks.graphCtor.mockImplementation(() => ({
      render: vi.fn(),
      on: vi.fn(),
      setElementState: vi.fn(),
      destroy: vi.fn(),
    }))
  })

  it('shows fallback error instead of crashing when G6 init throws', async () => {
    mocks.graphCtor.mockImplementation(() => {
      throw new Error('g6 init failed')
    })

    const wrapper = mount(KnowledgeGraph, {
      props: {
        treeData: validTreeData,
        masteryByParent: {},
      },
    })

    await nextTick()

    expect(wrapper.text()).toContain('g6 init failed')
  })

  it('shows fallback error when tree nodes payload is malformed', async () => {
    const wrapper = mount(KnowledgeGraph, {
      props: {
        treeData: {
          document_id: 1,
          nodes: null,
          total_nodes: 0,
        } as any,
        masteryByParent: {},
      },
    })

    await nextTick()

    expect(wrapper.text()).toContain('知识图数据异常，暂时无法渲染。')
    expect(mocks.graphCtor).not.toHaveBeenCalled()
  })
})
