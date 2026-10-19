import request from '@/utils/request'

/**
 * 获取用户列表
 * */
export function getUserPageList(params) {
  return request({
    url: '/api/user/list',
    method: 'get',
    params
  })
}

/**
 * 创建新用户
 * */
export function createUserApi(data) {
  return request({
    url: '/api/user',
    method: 'post',
    data
  })
}

/**
 * 编辑用户信息
 * */
export function updateUserApi(userId, data) {
  return request({
    url: `/api/user/${userId}`,
    method: 'put',
    data
  })
}

/**
 * 删除用户
 * */
export function deleteUserApi(userId) {
  return request({
    url: `/api/user/${userId}`,
    method: 'delete'
  })
}
