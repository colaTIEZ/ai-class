/** 知识树节点类型 - 与后端 schemas/knowledge_tree.py 严格对齐 */

export interface KnowledgeNode {
  node_id: string
  label: string
  parent_id: string | null
  content_summary: string
}

export interface KnowledgeNodeInDB extends KnowledgeNode {
  document_id: number
  depth: number
  chunk_text: string | null
  created_at: string
}

export interface KnowledgeTree {
  document_id: number
  nodes: KnowledgeNode[]
  total_nodes: number
}

/** 标准 API 响应信封 */
export interface ApiEnvelope<T = unknown> {
  status: 'success' | 'error'
  data: T
  message: string
  trace_id: string
}
