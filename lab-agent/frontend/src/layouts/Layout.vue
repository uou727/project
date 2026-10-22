<template>
  <div class="common-layout">
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
          align-items: center;
        "
      >
        <div
          style="flex: 1; display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img src="@/assets/imgs/logo.png" alt="Logo" style="height: 40px; margin-right: 10px" />
          <div>智能实验室预约系统</div>
        </div>
        <div>
          <el-dropdown>
            <div style="display: flex; align-items: center; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">{{ userInfo?.name }}</div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goPersion">个人信息</el-dropdown-item>
                <el-dropdown-item @click="goPassword">修改密码</el-dropdown-item>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu
            router
            :default-active="router.currentRoute.value.path"
            style="height: 100%"
            default-active="/manager/home"
          >
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              系统首页
            </el-menu-item>
            <el-menu-item index="/manager/lablist" v-if="userInfo?.role === 'student'">
              <el-icon><OfficeBuilding /></el-icon>
              实验室列表
            </el-menu-item>
            <el-menu-item index="/manager/lab" v-if="userInfo?.role === 'admin'">
              <el-icon><House /></el-icon>
              实验室管理
            </el-menu-item>
            <el-menu-item index="/manager/equipment" v-if="userInfo?.role === 'admin'">
              <el-icon><Setting /></el-icon>
              设备列表管理
            </el-menu-item>
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
              <el-icon><User /></el-icon>
              用户管理
            </el-menu-item>

            <el-menu-item index="/manager/my-reservation" v-if="userInfo?.role === 'student'">
              <el-icon><Tickets /></el-icon>
              <span>我的预约</span>
            </el-menu-item>
            <el-menu-item index="/manager/audit-reservation" v-if="userInfo?.role === 'admin'">
              <el-icon><DocumentChecked /></el-icon>
              <span>预约审核</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu as IconMenu,
  House,
  Setting,
  User,
  OfficeBuilding,
  Tickets,
  DocumentChecked
} from '@element-plus/icons-vue'

import { useRouter } from 'vue-router'
import { removeToken, removeUserInfo } from '@/utils/auth'
import { useUser } from '@/utils/user'
const { userInfo } = useUser()
const router = useRouter()
const handleLogout = () => {
  router.push('/login')
  removeToken()
  removeUserInfo()
}

const goPersion = () => {
  router.push('/manager/profile')
}

const goPassword = () => {
  router.push('/manager/password')
}
</script>
