<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getHealth, type HealthData } from '../api/client'

const healthStatus = ref<HealthData | null>(null)
const error = ref<string | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const response = await getHealth()
    if (response.status === 'success') {
      healthStatus.value = response.data
    } else {
      error.value = response.message || 'Unknown error'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to connect to backend'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">AI-Class</h1>
      <p class="text-gray-500 mb-6">智能学习平台</p>

      <div class="border rounded-xl p-4 mb-4">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          后端连通性检查
        </h2>

        <div v-if="loading" class="flex items-center justify-center gap-2 text-gray-400">
          <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <span>连接中...</span>
        </div>

        <div v-else-if="healthStatus" class="space-y-2">
          <div class="flex items-center justify-center gap-2 text-green-600">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="font-semibold">连接成功</span>
          </div>
          <div class="text-sm text-gray-500 space-y-1">
            <p>服务: {{ healthStatus.service }}</p>
            <p>版本: {{ healthStatus.version }}</p>
            <p>状态: {{ healthStatus.health }}</p>
          </div>
        </div>

        <div v-else-if="error" class="space-y-2">
          <div class="flex items-center justify-center gap-2 text-red-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span class="font-semibold">连接失败</span>
          </div>
          <p class="text-sm text-red-400">{{ error }}</p>
          <p class="text-xs text-gray-400 mt-2">请确保后端正在运行: uvicorn app.main:app --reload</p>
        </div>
      </div>

      <p class="text-xs text-gray-400">
        Vue 3 + Vite + TailwindCSS v4 | FastAPI + SQLite + LangGraph
      </p>
    </div>
  </div>
</template>
