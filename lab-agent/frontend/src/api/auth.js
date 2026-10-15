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

/**
 * 注册请求
 * */
export function registerApi(data) {
  return request({
    url: '/api/auth/register',
    method: 'post',
    data
  })
}

/**
 * 获取当前登录用户
 * */
export function getUserInfo(data) {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}

/**
 * 更新当前登录用户信息
 * */
export function updateUserInfo(data) {
  return request({
    url: '/api/user/me',
    method: 'put',
    data
  })
}

/** 修改当前用户密码 */
export function updatePasswordApi(data) {
  return request({
    url: '/api/user/password',
    method: 'put',
    data
  })
}
