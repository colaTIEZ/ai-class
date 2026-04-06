<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getRecentDocuments } from '../api/documents';

const router = useRouter();
const LAST_DOCUMENT_ID_KEY = 'ai-class-last-document-id';

const isResolving = ref(true);
const errorMsg = ref('');

function readCachedDocumentId(): number | null {
  const raw = window.localStorage.getItem(LAST_DOCUMENT_ID_KEY);
  const parsed = Number(raw);
  if (Number.isFinite(parsed) && parsed > 0) {
    return Math.trunc(parsed);
  }
  return null;
}

onMounted(async () => {
  const cachedId = readCachedDocumentId();
  if (cachedId) {
    await router.replace(`/documents/${cachedId}`);
    return;
  }

  try {
    const resp = await getRecentDocuments(1);
    const latest = resp.data?.document_ids?.[0];
    if (typeof latest === 'number' && latest > 0) {
      window.localStorage.setItem(LAST_DOCUMENT_ID_KEY, String(latest));
      await router.replace(`/documents/${latest}`);
      return;
    }
    await router.replace('/upload');
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : '无法定位最近文档';
    isResolving.value = false;
  }
});
</script>

<template>
  <div class="flex h-[60vh] items-center justify-center">
    <div class="text-center text-slate-500">
      <p v-if="isResolving">正在定位最近文档...</p>
      <div v-else>
        <p class="text-red-600">{{ errorMsg }}</p>
        <router-link to="/upload" class="mt-3 inline-block text-indigo-600 hover:underline">去上传页面</router-link>
      </div>
    </div>
  </div>
</template>