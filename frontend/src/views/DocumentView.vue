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
      <h1 class="text-3xl font-black text-slate-800 tracking-tight">🎯 圈定讨伐范围</h1>
      <div class="flex items-center gap-3">
        <router-link
          to="/upload"
          class="px-4 py-2 rounded-xl border-2 border-slate-200 text-slate-600 text-sm font-bold hover:bg-slate-100 hover:border-slate-300 transition-colors"
        >
          📜 解锁新卷轴
        </router-link>
        <div class="relative flex flex-col items-center justify-center">
          <transition name="bounce">
            <div v-if="quizStore.hasSelection" class="absolute -top-14 z-20 block w-max rounded-xl bg-orange-100 border border-orange-200 px-4 py-2 text-sm font-bold text-orange-700 shadow-lg pointer-events-none">
              <span class="mr-1">🎮</span>发现知识小怪，预计掉落经验值！
              <div class="absolute -bottom-2 left-1/2 -ml-2 h-4 w-4 rotate-45 bg-orange-100 border-b border-r border-orange-200"></div>
            </div>
          </transition>
          <button 
            @click="startQuiz" 
            :disabled="!quizStore.hasSelection"
            class="start-btn relative z-10 px-8 py-3 rounded-xl font-bold text-white shadow-sm transition-all duration-300"
            :class="quizStore.hasSelection ? 'bg-gradient-to-r from-orange-500 to-rose-500 hover:scale-105 hover:shadow-xl hover:shadow-orange-500/40 active:scale-95' : 'bg-slate-300 cursor-not-allowed'"
          >
            <span class="tracking-widest">⚔️ 立刻讨伐</span>
          </button>
        </div>
      </div>
    </div>

    <div class="content flex-grow mb-8 rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.04)] overflow-hidden bg-white/60 backdrop-blur-md border border-slate-200/60 p-2">
      <div v-if="isLoading" class="flex w-full h-full items-center justify-center">
        <div class="flex flex-col items-center gap-4">
          <div class="h-10 w-10 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"></div>
          <span class="text-sm font-bold tracking-widest text-indigo-400">正在具现化领地版图...</span>
        </div>
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
.bounce-enter-active {
  animation: bounce-in 0.6s cubic-bezier(0.68, -0.55, 0.26, 1.55) forwards;
}
.bounce-leave-active {
  animation: bounce-in 0.3s cubic-bezier(0.68, -0.55, 0.26, 1.55) reverse forwards;
}
@keyframes bounce-in {
  0% { transform: scale(0.5) translateY(20px); opacity: 0; }
  50% { transform: scale(1.05) translateY(-5px); opacity: 1; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}
</style>
