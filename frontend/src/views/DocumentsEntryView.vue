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
  <div class="mx-auto w-full max-w-5xl px-6 py-8">
    <div class="mb-5 flex items-center justify-between">
      <h1 class="text-3xl font-black text-slate-800 tracking-tight">选择要挑战的领地</h1>
      <router-link to="/upload" class="rounded-xl bg-orange-100 border border-orange-200 px-5 py-2.5 text-sm font-bold tracking-widest text-orange-700 hover:bg-orange-200 transition-all">
        ✨ 开启新领地
      </router-link>
    </div>

    <div v-if="isResolving" class="rounded-2xl border-2 border-slate-100 bg-white/50 p-10 text-center text-sm font-medium tracking-widest text-slate-400">
      正在探测领地坐标...
    </div>

    <div v-else-if="errorMsg" class="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
      <p>{{ errorMsg }}</p>
      <router-link to="/upload" class="mt-3 inline-block font-bold text-indigo-600 hover:underline">去获取</router-link>
    </div>

    <div v-else-if="documents.length === 0" class="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500">
      <p class="font-medium text-lg text-slate-600">当前没有已解析的魔法卷轴。</p>
      <router-link to="/upload" class="mt-4 inline-block rounded-lg bg-indigo-50 px-5 py-2 font-bold text-indigo-600 transition-colors hover:bg-indigo-100">📜 解读魔法卷轴</router-link>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="group w-full rounded-2xl border-2 border-slate-100 bg-white p-5 shadow-sm transition-all duration-300 hover:border-indigo-300 hover:shadow-lg hover:-translate-y-1 relative overflow-hidden"
      >
        <div class="absolute inset-0 bg-gradient-to-br from-indigo-50/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100"></div>
        <div class="relative z-10 flex flex-col h-full justify-between gap-4">
          <div>
            <p class="font-bold text-lg text-slate-800 line-clamp-2 leading-tight">{{ doc.title }}</p>
            <div class="mt-3 flex items-center gap-2">
               <span class="inline-flex rounded bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">ID: {{ doc.id }}</span>
               <span class="inline-flex rounded bg-emerald-50 border border-emerald-100 px-2.5 py-1 text-[10px] font-bold text-emerald-600">{{ doc.nodeCount }} 个节点</span>
            </div>
          </div>
          <div class="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
            <button
              type="button"
              class="w-full rounded-xl bg-slate-50 px-4 py-2.5 text-sm font-bold text-slate-700 transition-colors hover:bg-indigo-50 hover:text-indigo-700"
              @click="openDocument(doc.id)"
            >
              传送至领地
            </button>
            <button
              type="button"
              class="ml-2 rounded-xl p-2.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-60"
              title="销毁卷轴"
              :disabled="isDeleting(doc.id)"
              @click="removeDocument(doc.id)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                 <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>