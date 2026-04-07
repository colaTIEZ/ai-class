<script setup lang="ts">
// 主应用布局 — Glassmorphism 多层磨砂玻璃
</script>

<template>
  <div class="app-wrapper glass-background flex w-full min-h-screen">
    <!-- 侧边栏毛玻璃面板 -->
    <aside class="sidebar-glass w-64 flex flex-col fixed h-screen top-0 left-0 z-40">
      <div class="p-6 flex-1">
        <div class="logo font-black text-xl tracking-tight cursor-default select-none mb-8"
             style="color: var(--text-heading);">
          AI-Class
        </div>
        <nav class="flex flex-col gap-1.5 text-sm font-medium">
          <router-link to="/upload" class="nav-link w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200">
            <svg class="w-[18px] h-[18px] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <span>上传文档</span>
          </router-link>
          <router-link to="/documents" class="nav-link w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200">
            <svg class="w-[18px] h-[18px] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span>知识库</span>
          </router-link>
          <router-link to="/review" class="nav-link w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200">
            <svg class="w-[18px] h-[18px] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <span>错题回顾</span>
          </router-link>
        </nav>
      </div>

      <div class="p-6 mb-2">
        <router-link to="/documents" class="quiz-generate-btn w-full flex items-center justify-center px-4 py-2.5 font-semibold rounded-xl transition-all duration-200 text-sm">
          <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          生成测验
        </router-link>
      </div>
    </aside>

    <!-- 主内容区 — 第二层毛玻璃 -->
    <main class="main-content flex-1 ml-64 min-h-screen relative z-10">
      <div class="content-glass-layer">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style>
/* 侧边栏毛玻璃面板 */
.sidebar-glass {
  background: rgba(255, 255, 255, 0.30);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border-right: 1px solid rgba(255, 255, 255, 0.10);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.03);
}

/* 导航链接基础态 */
.nav-link {
  color: var(--text-muted-on-glass);
  position: relative;
  border-left: 3px solid transparent;
}

.nav-link:hover {
  color: var(--text-on-glass);
  background: rgba(255, 255, 255, 0.25);
}

/* 导航激活高亮 — 深色调实色背景 + 明亮左边框 */
.router-link-exact-active.nav-link {
  background: var(--accent-primary);
  color: #ffffff;
  font-weight: 600;
  border-left-color: #818CF8;
  box-shadow: 0 2px 10px rgba(67, 56, 202, 0.25);
}

/* "生成测验" 按钮 — 实色主色调 */
.quiz-generate-btn {
  background: var(--accent-primary);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(67, 56, 202, 0.30);
}

.quiz-generate-btn:hover {
  background: var(--accent-primary-hover);
  box-shadow: 0 6px 20px rgba(67, 56, 202, 0.40);
  transform: translateY(-1px);
}

/* 内容区毛玻璃层 */
.content-glass-layer {
  min-height: 100vh;
}

/* 全局字体抗锯齿 */
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
