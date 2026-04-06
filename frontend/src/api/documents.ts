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

export interface UploadQueueItem {
  job_id: string;
  status: 'queued' | 'processing' | 'done' | 'error' | 'unknown' | 'duplicate';
  position: number;
  duplicated?: boolean;
  existing_document_id?: number | null;
}

export interface UploadQueueResponse {
  status: 'success' | 'error';
  data: UploadQueueItem;
  message: string;
  trace_id: string;
}

export interface RecentDocumentsResponse {
  status: 'success' | 'error';
  data: {
    document_ids: number[];
  };
  message: string;
  trace_id: string;
}

function normalizeErrorMessage(response: Response, fallback: string): string {
  return `${fallback}: ${response.status} ${response.statusText}`;
}

export async function uploadPdf(file: File, force = false): Promise<UploadQueueResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`/api/v1/documents/upload?force=${force ? 'true' : 'false'}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(normalizeErrorMessage(response, 'Upload failed'));
  }

  return response.json();
}

export async function getUploadStatus(jobId: string): Promise<UploadQueueResponse> {
  const response = await fetch(`/api/v1/documents/upload/${jobId}`);
  if (!response.ok) {
    throw new Error(normalizeErrorMessage(response, 'Status query failed'));
  }
  return response.json();
}

export async function getDocumentTree(documentId: number): Promise<KnowledgeTree> {
  const response = await fetch(`/api/v1/documents/${documentId}/tree`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function getRecentDocuments(limit = 10): Promise<RecentDocumentsResponse> {
  const response = await fetch(`/api/v1/documents/recent?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
