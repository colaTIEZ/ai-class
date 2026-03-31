/**
 * 后端 API 客户端
 * 提供类型安全的 API 调用封装
 */

/** 标准 API 响应信封格式 */
export interface ApiEnvelope<T = unknown> {
  status: 'success' | 'error'
  data: T
  message: string
  trace_id: string
}

/** 健康检查响应数据 */
export interface HealthData {
  service: string
  version: string
  health: string
}

const API_BASE = '/api/v1'

/**
 * 通用 API 请求函数
 * 自动解析 JSON 并验证标准信封格式
 */
async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

/** 健康检查 API */
export async function getHealth(): Promise<ApiEnvelope<HealthData>> {
  return request<HealthData>('/health')
}
