<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getDocumentTree, getRecentDocuments, type KnowledgeTree } from '../api/documents';

const router = useRouter();
const LAST_DOCUMENT_ID_KEY = 'ai-class-last-document-id';

const isResolving = ref(true);
const errorMsg = ref('');
const documents = ref<Array<{ id: number; title: string; nodeCount: number }>>([]);

function readCachedDocumentId(): number | null {
  const raw = window.localStorage.getItem(LAST_DOCUMENT_ID_KEY);
  const parsed = Number(raw);
  if (Number.isFinite(parsed) && parsed > 0) {
    return Math.trunc(parsed);
  }
  return null;
}

function inferTitle(tree: KnowledgeTree, docId: number): string {
  const firstNamedNode = tree.nodes.find((n) => n.label && n.label !== 'Document Root');
  return firstNamedNode?.label || `文档 ${docId}`;
}

function openDocument(id: number) {
  window.localStorage.setItem(LAST_DOCUMENT_ID_KEY, String(id));
  router.push(`/documents/${id}`);
}

onMounted(async () => {
  const cachedId = readCachedDocumentId();

  try {
    const resp = await getRecentDocuments(20);
    const ids = (resp.data?.document_ids || []).filter((id) => typeof id === 'number' && id > 0);

    if (ids.length === 0) {
      if (cachedId) {
        documents.value = [{ id: cachedId, title: `文档 ${cachedId}`, nodeCount: 0 }];
      }
      isResolving.value = false;
      return;
    }

    const details = await Promise.allSettled(
      ids.map(async (id) => {
        const tree = await getDocumentTree(id);
        return {
          id,
          title: inferTitle(tree, id),
          nodeCount: tree.total_nodes,
        };
      }),
    );

    documents.value = details.map((item, idx) => {
      if (item.status === 'fulfilled') {
        return item.value;
      }
      const id = ids[idx];
      return {
        id,
        title: `文档 ${id}`,
        nodeCount: 0,
      };
    });
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : '无法加载文档列表';
  } finally {
    isResolving.value = false;
  }
});
</script>

<template>
  <div class="mx-auto w-full max-w-5xl px-6 py-8">
    <div class="mb-5 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-800">Study Material</h1>
      <router-link to="/upload" class="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">
        上传新文档
      </router-link>
    </div>

    <div v-if="isResolving" class="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
      正在加载文档列表...
    </div>

    <div v-else-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
      <p>{{ errorMsg }}</p>
      <router-link to="/upload" class="mt-3 inline-block text-indigo-600 hover:underline">去上传页面</router-link>
    </div>

    <div v-else-if="documents.length === 0" class="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
      <p>还没有可用文档，请先上传 PDF。</p>
      <router-link to="/upload" class="mt-3 inline-block text-indigo-600 hover:underline">去上传页面</router-link>
    </div>

    <div v-else class="space-y-3">
      <button
        v-for="doc in documents"
        :key="doc.id"
        type="button"
        class="w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-indigo-300 hover:shadow"
        @click="openDocument(doc.id)"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-semibold text-slate-800">{{ doc.title }}</p>
            <p class="mt-1 text-sm text-slate-500">document_id: {{ doc.id }}</p>
            <p class="text-sm text-slate-500">节点数: {{ doc.nodeCount }}</p>
          </div>
          <span class="rounded bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">打开</span>
        </div>
      </button>
    </div>
  </div>
</template>