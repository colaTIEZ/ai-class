<template>
  <div class="quiz-view p-8 max-w-3xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Quiz</h1>

    <!-- 加载状态 -->
    <div v-if="quizStore.isLoading" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Generating question...</p>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="quizStore.error"
      class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
    >
      <p class="text-red-700">{{ quizStore.error }}</p>
      <button
        @click="quizStore.resetQuiz()"
        class="mt-2 text-red-600 hover:underline"
      >
        Try again
      </button>
    </div>

    <!-- 问题显示 -->
    <div v-else-if="quizStore.hasQuestion" class="space-y-6">
      <div class="bg-white rounded-lg shadow-md p-6">
        <div class="flex items-center justify-between mb-4">
          <span
            class="inline-block px-3 py-1 text-sm font-medium rounded-full"
            :class="
              quizStore.questionType === 'multiple_choice'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-green-100 text-green-800'
            "
          >
            {{
              quizStore.questionType === 'multiple_choice'
                ? 'Multiple Choice'
                : 'Short Answer'
            }}
          </span>
        </div>

        <h2 class="text-xl font-semibold mb-4">
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
            class="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
            :class="quizStore.currentAnswer === option ? 'bg-indigo-50 border-indigo-300' : ''"
            @click="quizStore.currentAnswer = option"
          >
            <span class="font-medium mr-2">{{ String.fromCharCode(65 + index) }}.</span>
            {{ option }}
          </div>
        </div>

        <!-- 简答题输入框 -->
        <div v-else-if="quizStore.questionType === 'short_answer'" class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="w-full p-4 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            rows="4"
            placeholder="Type your answer here..."
          ></textarea>
        </div>
        <div v-else class="mt-4">
          <textarea
            v-model="quizStore.currentAnswer"
            class="w-full p-4 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            rows="3"
            placeholder="Type your answer here..."
          ></textarea>
        </div>

        <div class="mt-4 flex gap-2">
          <button
            @click="quizStore.submitAnswer('continue')"
            :disabled="quizStore.isStreaming"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-60"
          >
            {{ quizStore.isStreaming ? 'Thinking...' : 'Submit Answer' }}
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('show_answer')"
            :disabled="quizStore.isStreaming"
            class="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
          >
            Show Answer
          </button>
          <button
            v-if="quizStore.escapeHatchVisible"
            @click="quizStore.submitAnswer('skip')"
            :disabled="quizStore.isStreaming"
            class="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-60"
          >
            Skip Question
          </button>
        </div>

        <div v-if="quizStore.guardrailReason" class="mt-3 text-sm text-orange-700">
          Guardrail Trigger: {{ quizStore.guardrailReason }}
        </div>
        <div v-if="quizStore.needsReviewQueued" class="mt-2 text-sm text-blue-700">
          Marked as Needs Review for follow-up.
        </div>

        <div v-if="quizStore.currentHint" class="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p class="text-sm font-semibold text-yellow-800 mb-1">Socratic Hint</p>
          <p class="text-yellow-900">{{ quizStore.currentHint }}</p>
        </div>

        <details v-if="quizStore.traceLog.length" class="mt-4">
          <summary class="cursor-pointer text-sm text-gray-600">Trace Log</summary>
          <pre class="mt-2 p-3 text-xs bg-gray-50 border rounded overflow-auto max-h-56">{{ quizStore.traceLog }}</pre>
        </details>
      </div>

      <!-- 操作按钮 -->
      <div class="flex justify-between items-center">
        <router-link
          to="/"
          class="text-indigo-600 hover:underline flex items-center"
        >
          <span class="mr-1">&larr;</span> Back to Graph
        </router-link>
        <button
          @click="quizStore.resetQuiz()"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
        >
          New Question
        </button>
      </div>

      <!-- Trace ID (开发模式) -->
      <div v-if="quizStore.traceId" class="text-xs text-gray-400 mt-4">
        Trace ID: {{ quizStore.traceId }}
      </div>
    </div>

    <!-- 初始状态 - 显示选中的节点并开始 Quiz -->
    <div v-else class="space-y-6">
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-lg font-semibold mb-4">Selected Topics</h2>
        <ul v-if="quizStore.selectedNodeIds.length > 0" class="list-disc pl-6 space-y-1">
          <li v-for="id in quizStore.selectedNodeIds" :key="id" class="text-gray-700">
            {{ id }}
          </li>
        </ul>
        <p v-else class="text-gray-500">No topics selected. Please go back and select some topics.</p>
      </div>

      <div v-if="quizStore.hasSelection" class="flex gap-4">
        <button
          @click="quizStore.startQuiz('multiple_choice')"
          class="flex-1 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Start Multiple Choice Quiz
        </button>
        <button
          @click="quizStore.startQuiz('short_answer')"
          class="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          Start Short Answer Quiz
        </button>
      </div>

      <router-link
        to="/"
        class="inline-block text-indigo-600 hover:underline"
      >
        &larr; Back to Graph
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useQuizStore } from '../stores/quiz';
const quizStore = useQuizStore();
</script>
