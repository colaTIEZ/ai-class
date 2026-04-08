<template>
  <div class="quiz-view p-8 w-full flex gap-8">
    <div class="flex-1">
      <h1 class="text-2xl font-bold mb-6 tracking-tight" style="color: var(--text-heading);">练习模式</h1>

    <!-- 加载状态 -->
    <div v-if="quizStore.isLoading" class="text-center py-12">
      <div class="glass-spinner mx-auto" style="width: 3rem; height: 3rem;"></div>
      <p class="mt-4 text-sm font-medium" style="color: var(--text-muted-on-glass);">正在生成题目...</p>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="quizStore.error"
      class="glass-card-danger p-6 mb-6"
    >
      <p class="font-bold" style="color: rgba(185, 28, 28, 0.9);">{{ quizStore.error }}</p>
      <button
        @click="quizStore.resetQuiz()"
        class="mt-3 font-medium text-sm hover:underline"
        style="color: var(--color-danger);"
      >
        请重试
      </button>
    </div>

    <!-- 问题显示 -->
    <div v-else-if="quizStore.hasQuestion" class="space-y-6">
      <div class="glass-panel p-8">
        <div class="flex items-center justify-between mb-8">
          <span
            class="glass-badge px-3 py-1.5"
            :style="
              quizStore.questionType === 'multiple_choice'
                ? ''
                : 'background: var(--accent-primary-light); color: var(--accent-primary); border-color: var(--accent-primary-border);'
            "
          >
            {{
              quizStore.questionType === 'multiple_choice'
                ? '选择题'
                : '简答题'
            }}
          </span>
        </div>

        <h2 class="text-xl font-semibold leading-relaxed mb-8" style="color: var(--text-heading);">
          {{ quizStore.currentQuestion?.question_text }}
        </h2>

        <!-- 多选题选项 -->
        <div
          v-if="
            quizStore.questionType === 'multiple_choice' &&
            quizStore.currentQuestion?.options
          "
          class="space-y-3"
        >
          <div
            v-for="(option, index) in quizStore.currentQuestion.options"
            :key="index"
            class="glass-card p-4 cursor-pointer transition-all duration-200"
            :style="
              quizStore.currentAnswer === option
                ? 'background: var(--accent-primary-light); border-color: var(--accent-primary-border);'
                : ''
            "
            @click="quizStore.currentAnswer = option"
          >
            <span class="font-medium mr-2" style="color: var(--text-muted-on-glass);">{{ String.fromCharCode(65 + index) }}.</span>
            <span :style="quizStore.currentAnswer === option ? 'color: var(--accent-primary); font-weight: 600;' : 'color: var(--text-on-glass);'">{{ option }}</span>
          </div>
        </div>

        <!-- 简答题输入框 -->
        <div v-else-if="quizStore.questionType === 'short_answer'" class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="glass-input w-full p-4 resize-y"
            rows="4"
            placeholder="请输入您的答案..."
          ></textarea>
        </div>
        <div v-else class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="glass-input w-full p-4 resize-y"
            rows="3"
            placeholder="请输入您的答案..."
          ></textarea>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            @click="quizStore.submitAnswer('continue')"
            :disabled="quizStore.isStreaming"
            class="btn-primary px-6 py-2.5 text-sm"
          >
            {{ quizStore.isStreaming ? '生成提示中...' : '提交答案' }}
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('show_answer')"
            :disabled="quizStore.isStreaming"
            class="glass-btn px-4 py-2.5 text-sm disabled:opacity-60"
          >
            查看正确答案
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('skip')"
            :disabled="quizStore.isStreaming"
            class="px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60 cursor-pointer"
            style="color: var(--text-muted-on-glass); background: transparent;"
          >
            跳过此题
          </button>
        </div>

        <div v-if="quizStore.guardrailReason" class="glass-card-danger mt-4 px-3 py-2 text-xs font-bold flex items-center gap-2">
          <svg class="w-4 h-4 flex-shrink-0" style="color: var(--color-danger);" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <span style="color: var(--color-danger);">安全边界触发: {{ quizStore.guardrailReason }}</span>
        </div>
        <div v-if="quizStore.needsReviewQueued" class="glass-card mt-2 px-3 py-2 text-xs font-medium flex items-center gap-2" style="color: var(--text-on-glass);">
          <svg class="w-4 h-4 flex-shrink-0" style="color: var(--accent-primary);" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
          已被收入错题记录本。
        </div>

      </div>

      <!-- 操作按钮 -->
      <div class="flex justify-between items-center mt-6">
        <router-link
          to="/documents"
          class="text-sm font-medium transition-colors"
          style="color: var(--text-muted-on-glass);"
        >
          &larr; 返回
        </router-link>
        <button
          @click="quizStore.resetQuiz()"
          class="glass-btn px-4 py-2 text-sm"
        >
          下一题
        </button>
      </div>

      <details v-if="quizStore.traceLog.length" class="mt-4">
        <summary class="cursor-pointer text-sm" style="color: var(--text-muted-on-glass);">Trace Log ({{ quizStore.traceLog.length }})</summary>
        <ul class="mt-2 space-y-2 max-h-56 overflow-auto">
          <li
            v-for="(entry, index) in quizStore.traceLog"
            :key="`${entry.node_name}-${index}`"
            class="glass-card p-3"
          >
            <p class="text-sm font-semibold" style="color: var(--text-on-glass);">{{ entry.node_name }}</p>
            <pre class="mt-1 text-xs whitespace-pre-wrap" style="color: var(--text-muted-on-glass);">{{ formatTraceMetadata(entry.metadata) }}</pre>
          </li>
        </ul>
      </details>

      <!-- Trace ID (开发模式) -->
      <div v-if="quizStore.traceId" class="text-xs mt-4" style="color: var(--text-muted-on-glass); opacity: 0.5;">
        Trace ID: {{ quizStore.traceId }}
      </div>
    </div>

    <!-- 初始状态 - 显示选中的节点并开始 Quiz -->
    <div v-else class="space-y-6 flex-1">
      <div class="glass-panel p-8">
        <h2 class="text-lg font-semibold mb-4 tracking-tight" style="color: var(--text-heading);">当前选择的测验范围</h2>
        <ul v-if="quizStore.selectedNodeIds.length > 0" class="flex flex-wrap gap-2">
          <li v-for="id in quizStore.selectedNodeIds" :key="id" class="glass-badge px-2.5 py-1.5">
            {{ id }}
          </li>
        </ul>
        <div v-else class="glass-panel text-center py-6" style="border-style: dashed;">
           <p class="text-sm font-medium" style="color: var(--text-muted-on-glass);">请先选择要测验的知识节点。</p>
        </div>
      </div>

      <div v-if="quizStore.hasSelection" class="flex gap-4 mt-6">
        <button
          @click="quizStore.startQuiz('multiple_choice')"
          class="btn-primary flex-1 px-6 py-3 text-sm"
        >
          开始选择题
        </button>
        <button
          @click="quizStore.startQuiz('short_answer')"
          class="glass-btn flex-1 px-6 py-3 text-sm font-semibold"
          style="background: var(--glass-bg-deep);"
        >
          开始简答题
        </button>
      </div>

      <div class="text-center mt-6">
        <router-link
          to="/documents"
          class="inline-block text-sm font-medium transition-colors"
          style="color: var(--text-muted-on-glass);"
        >
          &larr; 返回
        </router-link>
      </div>
    </div>
    </div>

    <!-- 苏格拉底提示侧面板 — 蓝色半透明玻璃 -->
    <div v-if="quizStore.hasQuestion && quizStore.currentHint" class="w-80 flex-shrink-0">
      <transition name="fade">
        <div class="sticky top-8 rounded-xl p-5 socratic-hint-panel">
          <div class="flex items-center mb-3">
            <svg class="w-5 h-5 mr-2" style="color: #2563EB;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <span class="text-sm font-semibold tracking-wide" style="color: #1E40AF;">学习提示</span>
          </div>
          <p class="text-sm leading-relaxed" style="color: var(--text-heading);">{{ quizStore.displayedHint || quizStore.currentHint }}</p>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useQuizStore } from '../stores/quiz';

const quizStore = useQuizStore();



function formatTraceMetadata(metadata: Record<string, unknown>): string {
  try {
    return JSON.stringify(metadata, null, 2);
  } catch {
    return '无法解析数据';
  }
}
</script>

<style scoped>
/* 苏格拉底提示面板 — 蓝色半透明玻璃 */
.socratic-hint-panel {
  background: rgba(219, 234, 254, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(147, 197, 253, 0.3);
  box-shadow: 0 8px 32px rgba(37, 99, 235, 0.08);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
