<template>
  <div class="quiz-view p-8 max-w-3xl mx-auto">
    <h1 class="text-3xl font-black mb-6 text-slate-800 tracking-tight">📝 知识大挑战</h1>

    <!-- 加载状态 -->
    <div v-if="quizStore.isLoading" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
      <p class="mt-4 text-slate-500 font-bold tracking-widest">正在召唤考题...</p>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="quizStore.error"
      class="bg-rose-50 border border-rose-200 rounded-2xl p-6 mb-6"
    >
      <p class="text-rose-700 font-bold">{{ quizStore.error }}</p>
      <button
        @click="quizStore.resetQuiz()"
        class="mt-3 font-bold text-rose-600 hover:text-rose-800 hover:underline"
      >
        重新尝试召唤
      </button>
    </div>

    <!-- 问题显示 -->
    <div v-else-if="quizStore.hasQuestion" class="space-y-6">
      <div class="bg-white rounded-3xl border border-slate-100 shadow-[0_15px_40px_-15px_rgba(0,0,0,0.05)] p-8">
        <div class="flex items-center justify-between mb-6">
          <span
            class="inline-block px-4 py-1.5 text-xs font-black tracking-widest rounded-full"
            :class="
              quizStore.questionType === 'multiple_choice'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-emerald-100 text-emerald-700'
            "
          >
            {{
              quizStore.questionType === 'multiple_choice'
                ? '选择题阶段'
                : '简答题阶段'
            }}
          </span>
        </div>

        <h2 class="text-xl font-bold leading-relaxed text-slate-800 mb-6">
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
            class="p-4 border rounded-xl cursor-pointer transition-all duration-300"
            :class="[
              quizStore.currentAnswer === option 
                ? (quizStore.currentHint ? shakeClass : 'bg-indigo-50 border-indigo-300 shadow-md scale-[1.02]')
                : 'hover:bg-slate-50 border-slate-200 hover:shadow-sm'
            ]"
            @click="quizStore.currentAnswer = option"
          >
            <span class="font-bold mr-2 text-slate-500">{{ String.fromCharCode(65 + index) }}.</span>
            <span class="font-medium text-slate-800">{{ option }}</span>
          </div>
        </div>

        <!-- 简答题输入框 -->
        <div v-else-if="quizStore.questionType === 'short_answer'" class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="w-full p-5 border-2 border-slate-200 font-medium rounded-2xl focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
            rows="4"
            placeholder="请在此注入你的知识力量..."
          ></textarea>
        </div>
        <div v-else class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="w-full p-5 border-2 border-slate-200 font-medium rounded-2xl focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
            rows="3"
            placeholder="请在此注入你的知识力量..."
          ></textarea>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            @click="quizStore.submitAnswer('continue')"
            :disabled="quizStore.isStreaming"
            class="px-8 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-500 hover:shadow-lg hover:shadow-indigo-500/30 transition-all disabled:opacity-60 active:scale-95"
          >
            {{ quizStore.isStreaming ? '导师思考中...' : '提交答案' }}
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('show_answer')"
            :disabled="quizStore.isStreaming"
            class="px-6 py-3 bg-orange-500 text-white font-bold rounded-xl hover:bg-orange-400 hover:shadow-lg hover:shadow-orange-500/30 transition-all disabled:opacity-60 active:scale-95"
          >
            查看正确答案
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('skip')"
            :disabled="quizStore.isStreaming"
            class="px-6 py-3 bg-slate-300 text-slate-700 font-bold rounded-xl hover:bg-slate-200 transition-all disabled:opacity-60 active:scale-95"
          >
            跳过此题
          </button>
        </div>

        <div v-if="quizStore.guardrailReason" class="mt-4 text-xs font-bold text-rose-500 bg-rose-50 p-2 rounded-lg">
          ⚠️ 安全边界触发: {{ quizStore.guardrailReason }}
        </div>
        <div v-if="quizStore.needsReviewQueued" class="mt-2 text-xs font-bold text-sky-600 bg-sky-50 p-2 rounded-lg">
          📌 已被收入错题图鉴。
        </div>

        <transition name="spring">
          <div v-if="quizStore.currentHint" class="fixed bottom-6 lg:bottom-12 right-6 lg:right-12 z-50 w-80 max-w-[calc(100vw-3rem)] rounded-3xl border border-indigo-100 bg-white/95 p-5 shadow-[0_20px_60px_-15px_rgba(79,70,229,0.2)] backdrop-blur-xl">
            <!-- NPC Mascot -->
            <div class="absolute -top-10 -left-6 z-10 animate-[bounce_4s_infinite]">
               <div class="flex h-16 w-16 items-center justify-center rounded-full bg-orange-100 border-4 border-white shadow-xl text-3xl">🐱</div>
               <div class="absolute -bottom-2 left-6 h-4 w-4 bg-orange-100 border-r border-b border-orange-200 rotate-45 z-0 hidden"></div>
            </div>
            <div class="relative pt-2 pl-4">
              <p class="mb-2 text-xs font-black uppercase tracking-[0.2em] text-indigo-400">喵星导师的锦囊</p>
              <p class="text-sm font-semibold leading-relaxed text-slate-700">{{ quizStore.currentHint }}</p>
            </div>
          </div>
        </transition>

        <details v-if="quizStore.traceLog.length" class="mt-4">
          <summary class="cursor-pointer text-sm text-gray-600">Trace Log ({{ quizStore.traceLog.length }})</summary>
          <ul class="mt-2 space-y-2 max-h-56 overflow-auto">
            <li
              v-for="(entry, index) in quizStore.traceLog"
              :key="`${entry.node_name}-${index}`"
              class="rounded border bg-gray-50 p-3"
            >
              <p class="text-sm font-semibold text-gray-700">{{ entry.node_name }}</p>
              <pre class="mt-1 text-xs text-gray-600 whitespace-pre-wrap">{{ formatTraceMetadata(entry.metadata) }}</pre>
            </li>
          </ul>
        </details>
      </div>

      <!-- 操作按钮 -->
      <div class="flex justify-between items-center mt-8">
        <router-link
          to="/documents"
          class="text-slate-500 font-bold hover:text-indigo-600 flex items-center transition-colors px-4 py-2 bg-slate-100 rounded-xl hover:bg-indigo-50"
        >
          <span class="mr-2">&larr;</span> 撤退回领地
        </router-link>
        <button
          @click="quizStore.resetQuiz()"
          class="px-6 py-2 bg-indigo-50 text-indigo-700 font-bold rounded-xl hover:bg-indigo-100 transition-colors"
        >
          召唤下一题
        </button>
      </div>

      <!-- Trace ID (开发模式) -->
      <div v-if="quizStore.traceId" class="text-xs text-gray-400 mt-4">
        Trace ID: {{ quizStore.traceId }}
      </div>
    </div>

    <!-- 初始状态 - 显示选中的节点并开始 Quiz -->
    <div v-else class="space-y-6">
      <div class="bg-white rounded-3xl shadow-[0_15px_40px_-15px_rgba(0,0,0,0.05)] border border-slate-100 p-8">
        <h2 class="text-xl font-black text-slate-800 mb-4 tracking-tight">已圈定的范围</h2>
        <ul v-if="quizStore.selectedNodeIds.length > 0" class="flex flex-wrap gap-2">
          <li v-for="id in quizStore.selectedNodeIds" :key="id" class="px-3 py-1 bg-indigo-50 text-indigo-700 font-bold text-sm rounded-lg border border-indigo-100">
            {{ id }}
          </li>
        </ul>
        <div v-else class="text-center py-6 border-2 border-dashed border-slate-200 rounded-xl">
           <p class="text-slate-500 font-bold tracking-widest">❌ 未选择任何区域，请返回划定。</p>
        </div>
      </div>

      <div v-if="quizStore.hasSelection" class="flex gap-4 mt-6">
        <button
          @click="quizStore.startQuiz('multiple_choice')"
          class="flex-1 px-6 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-indigo-500/30 text-white font-bold rounded-2xl hover:scale-105 transition-all active:scale-95"
        >
          🚀 开启选择题
        </button>
        <button
          @click="quizStore.startQuiz('short_answer')"
          class="flex-1 px-6 py-4 bg-gradient-to-r from-emerald-500 to-teal-500 shadow-lg shadow-emerald-500/30 text-white font-bold rounded-2xl hover:scale-105 transition-all active:scale-95"
        >
          🚀 开启简答题
        </button>
      </div>

      <div class="text-center mt-6">
        <router-link
          to="/documents"
          class="inline-block text-slate-500 font-bold hover:text-indigo-600 transition-colors"
        >
          &larr; 返回重新选定
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useQuizStore } from '../stores/quiz';
import { watch, ref } from 'vue';
import confetti from 'canvas-confetti';

const quizStore = useQuizStore();

// Safe-to-Fail Peach Head-shake animation state
const shakeClass = ref('');
watch(() => quizStore.currentHint, (newHint) => {
  if (newHint) {
    shakeClass.value = 'animate-head-shake bg-orange-100 border-orange-300';
    // Remove the shake animation class after it completes to allow it to trigger again
    setTimeout(() => { 
      shakeClass.value = 'bg-orange-50 border-orange-200'; 
    }, 800);
  } else {
    shakeClass.value = '';
  }
});

// Dopamine Confetti on question advance (assumes correct answer caused the advance if it's the same quiz session)
watch(() => quizStore.currentQuestion, (newQ, oldQ) => {
  if (oldQ && newQ && oldQ.question_text !== newQ.question_text) {
     confetti({ 
       particleCount: 120, 
       spread: 80, 
       origin: { y: 0.6 },
       colors: ['#FF6B6B', '#4ECDC4', '#9D4EDD', '#F9CB28']
     });
  }
});

function formatTraceMetadata(metadata: Record<string, unknown>): string {
  return JSON.stringify(metadata, null, 2);
}
</script>

<style scoped>
@keyframes head-shake {
  0% { transform: translateX(0); }
  6.5% { transform: translateX(-6px) rotateY(-9deg); }
  18.5% { transform: translateX(5px) rotateY(7deg); }
  31.5% { transform: translateX(-3px) rotateY(-5deg); }
  43.5% { transform: translateX(2px) rotateY(3deg); }
  50% { transform: translateX(0); }
}
.animate-head-shake {
  animation: head-shake 0.8s ease-in-out;
}
.spring-enter-active {
  animation: spring-in 0.6s cubic-bezier(0.68, -0.55, 0.26, 1.55) forwards;
}
.spring-leave-active {
  animation: spring-in 0.4s reverse forwards;
}
@keyframes spring-in {
  0% { transform: scale(0.5) translateY(50px) rotate(-10deg); opacity: 0; }
  100% { transform: scale(1) translateY(0) rotate(0deg); opacity: 1; }
}
</style>
