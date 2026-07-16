import { useAuthStore } from '@/stores'

const API_BASE = '/api/v1/ai'

async function getHeaders(): Promise<Record<string, string>> {
  const authStore = useAuthStore()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }
  return headers
}

/** 获取模型列表 */
export async function fetchModels(apiBaseUrl: string, apiKey: string) {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/models`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ api_base_url: apiBaseUrl, api_key: apiKey }),
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.detail || '获取模型列表失败')
  }
  return resp.json()
}

/** 保存 AI 配置 */
export async function saveProvider(config: {
  provider_name: string
  api_base_url: string
  api_key: string
  model_name: string
  temperature: number
  max_tokens: number
  system_prompt?: string
}) {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/providers`, {
    method: 'POST',
    headers,
    body: JSON.stringify(config),
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.detail || '保存配置失败')
  }
  return resp.json()
}

/** 获取当前 AI 配置 */
export async function getProvider() {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/providers`, {
    method: 'GET',
    headers,
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.detail || '获取配置失败')
  }
  return resp.json()
}

/** 测试 AI 连接 */
export async function testConnection(apiBaseUrl: string, apiKey: string, modelName: string) {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/chat/test`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ api_base_url: apiBaseUrl, api_key: apiKey, model_name: modelName }),
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.detail || '连接测试失败')
  }
  return resp.json()
}

/** 发送聊天消息（SSE 流式） */
export async function sendChatMessage(
  sessionId: number | null,
  message: string,
  onDelta: (text: string) => void,
  onToolStart: (tool: string, args: any) => void,
  onToolEnd: (tool: string, result: string) => void,
  onDone: (sessionId: number, fullResponse: string) => void,
  onError: (error: string) => void,
  signal?: AbortSignal,
) {
  const headers = await getHeaders()
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })

  if (!response.ok) {
    const err = await response.json()
    onError(err.detail || '对话请求失败')
    return
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
        continue
      }
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (currentEvent === 'delta') {
            onDelta(data.content)
          } else if (currentEvent === 'tool_start') {
            onToolStart(data.tool, data.args)
          } else if (currentEvent === 'tool_end') {
            onToolEnd(data.tool, data.result)
          } else if (currentEvent === 'done') {
            onDone(data.session_id, data.full_response)
          } else if (currentEvent === 'error') {
            onError(data.error)
          }
        } catch (e) {
          // skip parse errors
        }
      }
      if (line === '') {
        currentEvent = ''
      }
    }
  }
}

/** 获取对话列表 */
export async function listSessions() {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/chat/sessions`, {
    method: 'GET',
    headers,
  })
  if (!resp.ok) throw new Error('获取对话列表失败')
  return resp.json()
}

/** 获取对话消息 */
export async function getSessionMessages(sessionId: number) {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: 'GET',
    headers,
  })
  if (!resp.ok) throw new Error('获取消息失败')
  return resp.json()
}

/** 删除对话 */
export async function deleteSession(sessionId: number) {
  const headers = await getHeaders()
  const resp = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    headers,
  })
  if (!resp.ok) throw new Error('删除对话失败')
  return resp.json()
}
