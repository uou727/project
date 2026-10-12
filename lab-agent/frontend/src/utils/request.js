import axios from 'axios'
import { getToken, logout } from './auth'
import { ElMessage } from 'element-plus'
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URLF,
  timeout: 30000
})

// 请求拦截配置
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bear ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// 返回拦截配置
service.interceptors.response.use(
  (res) => {
    const data = res.data
    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      if (data.code === 401) {
        logout()
        router.push('/login')
        return Promise.reject(data)
      }
    }
    return data
  },
  (err) => {
    if (err.response) {
      const hettpStatusCode = err.response.status
      if (hettpStatusCode === 401) {
        ElMessage.error('登录状态失效，请重新登陆')
        logout()
        router.push('/login')
        return Promise.reject(data)
      } else {
        ElMessage.error(err.response.data || '请求失败')
      }
    } else {
      ElMessage.error('网络异常，请检查后端服务')
    }
    return Promise.reject(err)
  }
)

export default service
