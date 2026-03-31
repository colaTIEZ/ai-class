<template>
  <div class="quiz-view p-8">
    <h1 class="text-3xl font-bold">Quiz Placeholder (Epic 2)</h1>
    <p class="mt-4">Selected Nodes from Epic 1:</p>
    <ul class="list-disc pl-6 mt-2">
      <li v-for="id in quizStore.selectedNodeIds" :key="id">{{ id }}</li>
    </ul>
    <router-link to="/" class="mt-6 inline-block text-indigo-600 hover:underline">&larr; Back to Graph</router-link>
  </div>
</template>

<script setup lang="ts">
import { useQuizStore } from '../stores/quiz';
const quizStore = useQuizStore();
</script>
