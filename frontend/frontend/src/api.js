import axios from 'axios'

const API = '/api'

let isRefreshing = false
let queue = []

axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axios.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    original._retry = true

    if (isRefreshing) {
      return new Promise((resolve) => {
        queue.push(() => resolve(axios(original)))
      })
    }

    isRefreshing = true
    try {
      const refresh = localStorage.getItem('refresh_token')
      const { data } = await axios.post(`${API}/token/refresh/`, { refresh })
      localStorage.setItem('access_token', data.access)
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
      queue.forEach((cb) => cb())
      queue = []
      return axios(original)
    } catch (e) {
      localStorage.clear()
      window.location.href = '/'
      return Promise.reject(e)
    } finally {
      isRefreshing = false
    }
  }
)

export default axios
export { API }