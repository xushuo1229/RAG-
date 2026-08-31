import request from './request'

export function fetchConversations() {
  return request.get('/conversations')
}

export function fetchMessages(id) {
  return request.get(`/conversations/${id}/messages`)
}

export function removeConversation(id) {
  return request.delete(`/conversations/${id}`)
}

/**
 * 流式问答（SSE）：用 fetch + ReadableStream 逐段解析。
 * handlers: { onSources, onDelta, onDone, onError, onEvent }
 */
export async function askStream({ question, conversation_id }, handlers = {}) {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question, conversation_id }),
  })

  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || '请求失败')
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const handleLine = (line) => {
    const trimmed = line.trim()
    if (!trimmed.startsWith('data:')) return
    const payload = trimmed.slice(5).trim()
    if (!payload) return
    let parsed
    try {
      parsed = JSON.parse(payload)
    } catch {
      return
    }
    const { type, data } = parsed
    handlers.onEvent?.(type, data)
    if (type === 'sources') handlers.onSources?.(data)
    else if (type === 'delta') handlers.onDelta?.(data)
    else if (type === 'done') handlers.onDone?.(data)
    else if (type === 'error') handlers.onError?.(data)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    parts.forEach(handleLine)
  }
  if (buffer.trim()) handleLine(buffer)
}