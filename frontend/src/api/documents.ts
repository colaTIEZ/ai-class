export interface KnowledgeNode {
  node_id: string;
  label: string;
  parent_id: string | null;
  content_summary: string;
}

export interface KnowledgeTree {
  document_id: number;
  nodes: KnowledgeNode[];
  total_nodes: number;
}

export async function getDocumentTree(documentId: number): Promise<KnowledgeTree> {
  const response = await fetch(`/api/v1/documents/${documentId}/tree`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
