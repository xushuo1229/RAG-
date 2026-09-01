import request from './request'

export function fetchStats() {
  return request.get('/stats')
}