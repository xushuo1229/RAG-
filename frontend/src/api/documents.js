import request from './request'

export function fetchDocuments() {
  return request.get('/documents')
}

export function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/documents', form, { timeout: 300000 })
}

export function removeDocument(id) {
  return request.delete(`/documents/${id}`)
}