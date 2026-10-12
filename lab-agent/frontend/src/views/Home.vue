<template>
  <div>系统首页{{ userInfo?.name }}</div>
</template>

<script setup>
import { useUser } from '@/utils/user'
const { userInfo } = useUser()
</script>
