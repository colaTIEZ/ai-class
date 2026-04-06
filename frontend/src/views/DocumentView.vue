<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getDocumentTree } from '../api/documents';
import { getChapterMastery } from '../api/review';
import type { KnowledgeTree } from '../api/documents';
import KnowledgeGraph from '../components/graph/KnowledgeGraph.vue';
import { useQuizStore } from '../stores/quiz';

const route = useRoute();
const router = useRouter();
const quizStore = useQuizStore();

const documentId = computed(() => Number(route.params.id));
const treeData = ref<KnowledgeTree | null>(null);
const masteryByParent = ref<Record<string, number>>({});
const isLoading = ref(true);
const errorMsg = ref('');

onMounted(async () => {
  try {
    isLoading.value = true;
    quizStore.setActiveDocument(documentId.value);
    treeData.value = await getDocumentTree(documentId.value);
  } catch (err: any) {
    errorMsg.value = err.message || 'Failed to load document structure';
  }

  try {
    const masteryResponse = await getChapterMastery();
    if (masteryResponse.status === 'success' && masteryResponse.data) {
      masteryByParent.value = Object.fromEntries(
        masteryResponse.data.by_parent.map((item) => [item.parent_id, item.mastery_score])
      );
    } else {
      masteryByParent.value = {};
    }
  } catch {
    // Keep graph rendering even if mastery fetch fails.
    masteryByParent.value = {};
  } finally {
    isLoading.value = false;
  }
});

const startQuiz = () => {
  if (quizStore.hasSelection) {
    router.push('/quiz');
  }
};
</script>

<template>
  <div class="document-view w-full h-screen flex flex-col pt-16 px-8 bg-slate-50">
    <div class="header flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold text-slate-800 tracking-tight">Select Study Scope</h1>
      <div class="flex items-center gap-3">
        <router-link
          to="/upload"
          class="px-4 py-2 rounded-md border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-100 transition-colors"
        >
          Upload PDF
        </router-link>
        <button 
          @click="startQuiz" 
          :disabled="!quizStore.hasSelection"
          class="start-btn px-6 py-2.5 rounded-md font-medium text-white shadow-sm transition-all duration-200"
          :class="quizStore.hasSelection ? 'bg-indigo-600 hover:bg-indigo-700 active:scale-95' : 'bg-slate-300 cursor-not-allowed'"
        >
          Start Quiz
        </button>
      </div>
    </div>

    <div class="content flex-grow mb-8 rounded-xl shadow-sm overflow-hidden bg-white border border-slate-200">
      <div v-if="isLoading" class="flex w-full h-full items-center justify-center">
        <span class="text-slate-400">Loading hierarchy...</span>
      </div>
      <div v-else-if="errorMsg" class="flex w-full h-full items-center justify-center">
        <span class="text-red-500 font-medium">{{ errorMsg }}</span>
      </div>
      <div v-else-if="treeData && treeData.total_nodes === 0" class="flex w-full h-full items-center justify-center">
        <div class="text-center text-slate-500">
          <p class="font-medium">当前文档没有可展示的知识节点。</p>
          <p class="mt-1 text-sm">请先上传并处理 PDF，或切换到最近上传的文档。</p>
          <router-link to="/upload" class="mt-3 inline-block text-indigo-600 hover:underline">去上传页面</router-link>
        </div>
      </div>
      <KnowledgeGraph v-else-if="treeData" :treeData="treeData" :masteryByParent="masteryByParent" />
    </div>
  </div>
</template>

<style scoped>
</style>
