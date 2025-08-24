import axios from 'axios'

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Agent types
export interface Agent {
  id: string
  name: string
  type: string
  status: 'active' | 'idle' | 'busy' | 'error' | 'unknown'
  session: string
  window: number
  lastActivity: string
  stateDetails?: {
    idleCount: number
    contentBasedState: string
    lastContentCheck: string
  }
}

export interface Session {
  name: string
  windows: number[]
  created: string
  attached: boolean
}

export interface SystemStatus {
  daemonStatus: {
    monitor: {
      running: boolean
      pid: number | null
      uptimeSeconds?: number
    }
    messaging: {
      running: boolean
      pid: number | null
    }
  }
  summary: {
    totalAgents: number
    active: number
    idle: number
    error: number
    busy: number
    unknown: number
  }
}

// API endpoints
export const agentApi = {
  list: () => api.get<Agent[]>('/agents/list'),

  getStatus: (sessionWindow: string) =>
    api.get<Agent>(`/agents/${sessionWindow}/status`),

  sendMessage: (sessionWindow: string, message: string) =>
    api.post(`/agents/${sessionWindow}/message`, { message }),

  spawn: (role: string, sessionWindow: string, briefing?: string) =>
    api.post('/agents/spawn', { role, session_window: sessionWindow, briefing }),

  kill: (sessionWindow: string) =>
    api.delete(`/agents/${sessionWindow}`),
}

export const sessionApi = {
  list: () => api.get<Session[]>('/sessions/list'),

  create: (name: string) =>
    api.post('/sessions/create', { name }),

  delete: (name: string) =>
    api.delete(`/sessions/${name}`),
}

export const monitoringApi = {
  getStatus: () => api.get<SystemStatus>('/monitoring/status'),

  getMetrics: () => api.get('/monitoring/metrics'),
}

export const commandApi = {
  execute: (command: string, args?: string[]) =>
    api.post('/commands/execute', { command, args }),

  getHistory: () => api.get('/commands/history'),
}

export default api
