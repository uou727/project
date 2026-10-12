import request from '@/utils/request'

/**
 * 登录请求
 * */
export function loginApi(data) {
  console.log(import.meta.env.VITE_API_BASE_URL + '/api/auth/login')
  return request({
    url: '/api/auth/login',
    method: 'post',
    data
  })
}
