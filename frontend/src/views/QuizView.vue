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
          >
            <span class="font-medium mr-2">{{ String.fromCharCode(65 + index) }}.</span>
            {{ option }}
          </div>
        </div>

        <!-- 简答题输入框 -->
        <div v-else-if="quizStore.questionType === 'short_answer'" class="mt-4">
          <textarea
            class="w-full p-4 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            rows="4"
            placeholder="Type your answer here..."
          ></textarea>
        </div>
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
