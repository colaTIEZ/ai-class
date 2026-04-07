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

function isValidDocumentId(id: number): boolean {
  return Number.isFinite(id) && id > 0;
}

function normalizeTreePayload(payload: unknown): KnowledgeTree {
  const raw = payload as { data?: unknown };
  const candidate = (raw && typeof raw === 'object' && 'data' in raw ? raw.data : payload) as Partial<KnowledgeTree> | undefined;

  if (!candidate || typeof candidate !== 'object' || !Array.isArray(candidate.nodes)) {
    throw new Error('知识树数据格式异常，请重新上传文档后重试');
  }

  return {
    document_id: Number(candidate.document_id ?? documentId.value),
    nodes: candidate.nodes,
    total_nodes: Number.isFinite(candidate.total_nodes as number)
      ? Number(candidate.total_nodes)
      : candidate.nodes.length,
  };
}

onMounted(async () => {
  if (!isValidDocumentId(documentId.value)) {
    errorMsg.value = '文档 ID 无效，请从上传页重新进入。';
    isLoading.value = false;
    return;
  }

  try {
    isLoading.value = true;
    quizStore.setActiveDocument(documentId.value);
    const treePayload = await getDocumentTree(documentId.value);
    treeData.value = normalizeTreePayload(treePayload);
  } catch (err: any) {
    errorMsg.value = err.message || '文档结构加载失败';
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
    // 掌握度加载失败不阻塞图谱渲染
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
  <div class="document-view w-full h-screen flex flex-col px-8 py-10 overflow-hidden">
    <!-- 头部区域 -->
    <div class="header flex justify-between items-center mb-6 w-full">
      <h1 class="text-3xl font-bold tracking-tight" style="color: var(--text-heading);">选择测验范围</h1>
      <div class="flex items-center gap-3">
        <router-link
          to="/upload"
          class="glass-btn px-4 py-2.5 flex items-center gap-2 text-sm"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          上传新文档
        </router-link>
        <div class="relative flex flex-col items-center justify-center">
          <button
            @click="startQuiz"
            :disabled="!quizStore.hasSelection"
            class="relative z-10 px-6 py-2.5 rounded-xl font-medium text-sm transition-all duration-200"
            :class="quizStore.hasSelection ? 'btn-primary' : ''"
            :style="!quizStore.hasSelection ? 'background: rgba(148, 163, 184, 0.3); color: var(--text-muted-on-glass); cursor: not-allowed; box-shadow: none;' : ''"
          >
            <span>开始测验</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="content flex-1 w-full relative">
      <!-- 加载态 -->
      <div v-if="isLoading" class="flex w-full h-full items-center justify-center">
        <div class="flex flex-col items-center gap-4">
          <div class="glass-spinner" style="width: 2.5rem; height: 2.5rem;"></div>
          <span class="text-sm font-medium" style="color: var(--text-muted-on-glass);">正在渲染知识图谱...</span>
        </div>
      </div>
      <!-- 错误态 -->
      <div v-else-if="errorMsg" class="flex w-full h-full items-center justify-center">
        <div class="glass-card-danger px-6 py-4 rounded-xl">
          <span class="font-medium" style="color: rgba(185, 28, 28, 0.9);">{{ errorMsg }}</span>
        </div>
      </div>
      <!-- 空节点态 -->
      <div v-else-if="treeData && treeData.total_nodes === 0" class="flex w-full h-full items-center justify-center">
        <div class="glass-panel text-center px-8 py-10">
          <svg class="w-12 h-12 mx-auto mb-4" style="color: var(--text-muted-on-glass); opacity: 0.4;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p class="font-medium" style="color: var(--text-on-glass);">当前文档没有可展示的知识节点。</p>
          <p class="mt-1 text-sm" style="color: var(--text-muted-on-glass);">请先上传并处理 PDF，或切换到最近上传的文档。</p>
          <router-link to="/upload" class="mt-4 btn-primary inline-block px-5 py-2 text-sm">去上传</router-link>
        </div>
      </div>
      <!-- 知识图谱 -->
      <KnowledgeGraph v-else-if="treeData" :treeData="treeData" :masteryByParent="masteryByParent" />
    </div>
  </div>
</template>

<style scoped>
/* 极简样式 — 继承全局 Glassmorphism 设计系统 */
</style>
