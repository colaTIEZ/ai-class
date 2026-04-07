<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { deleteDocument, getDocumentTree, getRecentDocuments, type KnowledgeTree } from '../api/documents';

const router = useRouter();
const LAST_DOCUMENT_ID_KEY = 'ai-class-last-document-id';

const isResolving = ref(true);
const errorMsg = ref('');
const documents = ref<Array<{ id: number; title: string; nodeCount: number }>>([]);
const deletingIds = ref<number[]>([]);

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

function isDeleting(id: number): boolean {
  return deletingIds.value.includes(id);
}

async function removeDocument(id: number) {
  if (isDeleting(id)) {
    return;
  }

  const ok = window.confirm(`确认删除文档 ${id} 吗？此操作不可撤销。`);
  if (!ok) {
    return;
  }

  deletingIds.value = [...deletingIds.value, id];
  try {
    await deleteDocument(id);
    documents.value = documents.value.filter((d) => d.id !== id);
    if (Number(window.localStorage.getItem(LAST_DOCUMENT_ID_KEY)) === id) {
      window.localStorage.removeItem(LAST_DOCUMENT_ID_KEY);
    }
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : '删除文档失败';
  } finally {
    deletingIds.value = deletingIds.value.filter((x) => x !== id);
  }
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
  <div class="w-full px-8 py-10">
    <!-- 标题栏 -->
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-3xl font-bold tracking-tight" style="color: var(--text-heading);">选择文档</h1>
      <router-link to="/upload" class="glass-btn px-5 py-2.5 text-sm flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        上传新文档
      </router-link>
    </div>

    <!-- 加载态 -->
    <div v-if="isResolving" class="glass-panel p-10 text-center">
      <div class="flex items-center justify-center gap-3">
        <div class="glass-spinner"></div>
        <span class="text-sm font-medium" style="color: var(--text-muted-on-glass);">正在加载文档列表...</span>
      </div>
    </div>

    <!-- 错误态 -->
    <div v-else-if="errorMsg" class="glass-card-danger p-6">
      <p style="color: rgba(185, 28, 28, 0.9);">{{ errorMsg }}</p>
      <router-link to="/upload" class="mt-3 inline-block font-medium text-sm hover:underline" style="color: var(--accent-primary);">去上传</router-link>
    </div>

    <!-- 空态 -->
    <div v-else-if="documents.length === 0" class="glass-panel empty-state px-6">
      <svg class="w-12 h-12 mb-4" style="color: var(--text-muted-on-glass); opacity: 0.5;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="font-semibold text-lg" style="color: var(--text-on-glass);">当前没有已处理的文档材料。</p>
      <router-link to="/upload" class="mt-4 btn-primary inline-block px-5 py-2 text-sm">
        上传文档
      </router-link>
    </div>

    <!-- 文档卡片网格 -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="glass-card p-5 cursor-pointer group relative overflow-hidden"
      >
        <div class="relative z-10 flex flex-col h-full justify-between gap-4">
          <div>
            <p class="font-semibold text-lg line-clamp-2 leading-tight" style="color: var(--text-heading);">{{ doc.title }}</p>
            <div class="mt-3 flex items-center gap-2">
               <span class="glass-badge text-xs" style="opacity: 0.6;">ID: {{ doc.id }}</span>
               <span class="glass-badge text-xs" style="background: var(--accent-primary-light); color: var(--accent-primary); border-color: var(--accent-primary-border);">{{ doc.nodeCount }} 个节点</span>
            </div>
          </div>
          <div class="mt-4 flex items-center justify-between pt-3" style="border-top: 1px solid var(--glass-border);">
            <button
              type="button"
              class="glass-btn w-full px-4 py-2 text-sm"
              @click="openDocument(doc.id)"
            >
              查看详情
            </button>
            <button
              type="button"
              class="ml-2 rounded-lg p-2 transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
              style="color: var(--text-muted-on-glass);"
              title="删除文档"
              :disabled="isDeleting(doc.id)"
              @click="removeDocument(doc.id)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 transition-colors hover:text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>