import { defineStore } from 'pinia'
import axios, { API } from '../api'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export const useChatStore = defineStore('chat', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || null,
    refreshToken: localStorage.getItem('refresh_token') || null,
    messages: [],
    socket: null,
    connected: false,
    reconnectAttempts: 0,
    heartbeatTimer: null,
    reconnectTimer: null,
    missedPongs: 0,
    currentRoomId: null,
    lastError: null,
    typingUsers: new Set(),
  }),

  getters: {
    isAuthenticated: (s) => !!s.accessToken,
  },

  actions: {
    async login(username, password) {
      const { data } = await axios.post(`${API}/token/`, { username, password })
      this.accessToken = data.access
      this.refreshToken = data.refresh
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
    },

    logout() {
      this.disconnect()
      this.accessToken = this.refreshToken = null
      localStorage.clear()
    },

    async fetchHistory(roomId) {
      const { data } = await axios.get(`${API}/messages/?room=${roomId}`)
      this.messages = data
    },

    async loadOlder(roomId) {
      const oldest = this.messages[0]?.id
      if (!oldest) return
      const { data } = await axios.get(
        `${API}/messages/?room=${roomId}&before=${oldest}`
      )
      this.messages = [...data, ...this.messages]
    },

    connect(roomId) {
      if (this.socket) this.disconnect()
      this.currentRoomId = roomId
      this.lastError = null

      const url = `${WS_BASE}/ws/chat/${roomId}/`
      const protocols = [`access_token.${this.accessToken}`]
      this.socket = new WebSocket(url, protocols)

      this.socket.onopen = () => {
        this.connected = true
        this.reconnectAttempts = 0
        this.missedPongs = 0
        this.startHeartbeat()
      }

      this.socket.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'pong') {
          this.missedPongs = 0
          return
        }
        if (msg.type === 'typing') {
          this.typingUsers.add(msg.user)
          setTimeout(() => this.typingUsers.delete(msg.user), 2000)
          return
        }
        if (msg.type === 'error') {
          this.lastError = msg.code
          return
        }
        // Обычное сообщение
        this.messages.push(msg)
      }

      this.socket.onclose = async (event) => {
        this.connected = false
        this.stopHeartbeat()

        if (event.code === 4401) {
          // Пробуем refresh токена
          try {
            const refresh = localStorage.getItem('refresh_token')
            const { data } = await axios.post(`${API}/token/refresh/`, { refresh })
            this.accessToken = data.access
            localStorage.setItem('access_token', data.access)
            if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
            this.connect(roomId)
            return
          } catch {
            this.logout()
            return
          }
        }

        if (event.code === 4403) {
          this.lastError = 'not_a_member'
          return
        }

        // Экспоненциальный backoff
        const delay = Math.min(3000 * Math.pow(2, this.reconnectAttempts), 30000)
        this.reconnectAttempts++
        this.reconnectTimer = setTimeout(() => this.connect(roomId), delay)
      }
    },

    startHeartbeat() {
      this.heartbeatTimer = setInterval(() => {
        if (this.socket?.readyState !== WebSocket.OPEN) return
        if (this.missedPongs >= 2) {
          this.socket.close(4000, 'heartbeat_timeout')
          return
        }
        this.missedPongs++
        this.socket.send(JSON.stringify({ type: 'ping' }))
      }, 25000)
    },

    stopHeartbeat() {
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer)
        this.heartbeatTimer = null
      }
    },

    send(content) {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return
      const clientId = crypto.randomUUID()
      this.messages.push({
        id: `tmp-${clientId}`,
        client_id: clientId,
        content,
        author: 'Вы',
        pending: true,
        created_at: new Date().toISOString(),
      })
      this.socket.send(JSON.stringify({ content, client_id: clientId }))
    },

    sendTyping() {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'typing' }))
      }
    },

    disconnect() {
      this.stopHeartbeat()
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }
      this.socket?.close()
      this.socket = null
      this.connected = false
    },
  },
})