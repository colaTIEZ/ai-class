<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getUploadStatus, uploadPdf, type UploadQueueItem } from '../api/documents';

const router = useRouter();
const LAST_DOCUMENT_ID_KEY = 'ai-class-last-document-id';

const selectedFile = ref<File | null>(null);
const isUploading = ref(false);
const isPolling = ref(false);
const uploadError = ref('');
const uploadResult = ref<UploadQueueItem | null>(null);
const pollingError = ref('');
const rawJobId = ref('');
const duplicateDocumentId = ref<number | null>(null);

let pollingTimer: number | null = null;

const canUpload = computed(() => !!selectedFile.value && !isUploading.value);

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
  uploadError.value = '';
}

function cleanupPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer);
    pollingTimer = null;
  }
  isPolling.value = false;
}

function deriveDocumentIdFromJobId(jobId: string): number {
  return Number.parseInt(jobId.replace(/-/g, '').slice(0, 8), 16);
}

async function pollStatusOnce(jobId: string) {
  try {
    const statusResp = await getUploadStatus(jobId);
    uploadResult.value = statusResp.data;
    pollingError.value = '';

    if (statusResp.data.status === 'done') {
      cleanupPolling();
      const documentId = deriveDocumentIdFromJobId(jobId);
      window.localStorage.setItem(LAST_DOCUMENT_ID_KEY, String(documentId));
      await router.push(`/documents/${documentId}`);
      return;
    }

    if (statusResp.data.status === 'error') {
      cleanupPolling();
      pollingError.value = '文档处理失败，请重新上传。';
    }
  } catch (err: unknown) {
    cleanupPolling();
    pollingError.value = err instanceof Error ? err.message : '轮询失败';
  }
}

async function startUpload(force = false) {
  if (!selectedFile.value || isUploading.value) {
    return;
  }

  uploadError.value = '';
  pollingError.value = '';
  duplicateDocumentId.value = null;
  isUploading.value = true;
  cleanupPolling();

  try {
    const resp = await uploadPdf(selectedFile.value, force);
    uploadResult.value = resp.data;
    rawJobId.value = resp.data.job_id;

    if (resp.data.status === 'duplicate' && resp.data.existing_document_id) {
      duplicateDocumentId.value = resp.data.existing_document_id;
      return;
    }

    isPolling.value = true;
    pollingTimer = window.setInterval(() => {
      void pollStatusOnce(resp.data.job_id);
    }, 1500);

    await pollStatusOnce(resp.data.job_id);
  } catch (err: unknown) {
    uploadError.value = err instanceof Error ? err.message : '上传失败';
  } finally {
    isUploading.value = false;
  }
}

onUnmounted(() => {
  cleanupPolling();
});

async function reuseExistingDocument() {
  if (!duplicateDocumentId.value) {
    return;
  }
  window.localStorage.setItem(LAST_DOCUMENT_ID_KEY, String(duplicateDocumentId.value));
  await router.push(`/documents/${duplicateDocumentId.value}`);
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-6 py-10">
    <div class="rounded-3xl border border-slate-200/80 bg-white/85 p-8 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center justify-center rounded-xl bg-orange-100 p-2 text-orange-600 shadow-sm">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </span>
        <h1 class="text-3xl font-black text-slate-800">点亮知识领地</h1>
      </div>
      <p class="mt-3 text-sm leading-6 text-slate-600">
        上传魔法卷轴 (PDF)，AI 将施展“知识凝练术”为您开辟专属的天赋树。
      </p>

      <div class="mt-8 rounded-2xl border-2 border-dashed border-indigo-200 bg-indigo-50/50 p-6 transition-all hover:border-indigo-400 hover:bg-indigo-50">
        <input
          type="file"
          accept="application/pdf,.pdf"
          @change="onFileChange"
          class="block w-full text-sm text-slate-500 file:mr-4 file:rounded-full file:border-0 file:bg-indigo-100 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-indigo-700 hover:file:bg-indigo-200"
        />
        <p v-if="selectedFile" class="mt-4 inline-block rounded-lg bg-white px-3 py-1 text-sm font-medium text-indigo-800 shadow-sm">
          卷轴已就绪: {{ selectedFile.name }} ({{ Math.ceil(selectedFile.size / 1024) }} KB)
        </p>
      </div>

      <div class="mt-8 flex items-center justify-center gap-4">
        <button
          :disabled="!canUpload"
          @click="() => startUpload()"
          class="group relative overflow-hidden rounded-2xl bg-indigo-600 px-8 py-3 text-base font-bold text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500 hover:shadow-indigo-600/50 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
        >
          <span class="relative z-10 flex items-center gap-2">
            <span v-if="!isUploading">⚡ 施放提取术</span>
            <span v-else>✨ 咒语吟唱中...</span>
          </span>
          <div class="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-1000 group-hover:translate-x-full"></div>
        </button>

        <router-link
          to="/documents"
          class="rounded-xl px-4 py-3 text-sm font-semibold text-slate-500 transition-colors hover:text-slate-800"
        >
          去图鉴看看
        </router-link>
      </div>

      <div v-if="duplicateDocumentId" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p class="text-sm text-amber-800">
          检测到重复文件，可直接复用已有文档（ID: {{ duplicateDocumentId }})，或强制重新上传。
        </p>
        <div class="mt-3 flex gap-3">
          <button
            @click="reuseExistingDocument"
            class="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            复用已有文档
          </button>
          <button
            :disabled="isUploading"
            @click="startUpload(true)"
            class="rounded-md border border-amber-400 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            强制重新上传
          </button>
        </div>
      </div>

      <p v-if="uploadError" class="mt-4 text-sm font-medium text-red-600">{{ uploadError }}</p>

      <!-- AI Extraction Animation (Magic Aura) -->
      <div v-if="isPolling" class="mt-10 flex flex-col items-center justify-center pb-6">
        <div class="relative flex h-24 w-24 items-center justify-center">
          <div class="absolute h-full w-full animate-ping rounded-full bg-indigo-400 opacity-20"></div>
          <div class="absolute h-16 w-16 animate-[spin_3s_linear_infinite] rounded-full border-4 border-dashed border-indigo-300 opacity-60"></div>
          <div class="absolute h-8 w-8 rounded-full bg-indigo-600 shadow-[0_0_20px_#4f46e5]"></div>
          <div class="absolute -top-2 h-3 w-3 animate-bounce rounded-full bg-orange-400 shadow-[0_0_10px_#fb923c]"></div>
        </div>
        <p class="mt-6 text-sm font-bold text-indigo-700">正在提炼核心考点... 魔法纯度极高 ✨</p>
      </div>

      <div v-else-if="uploadResult && uploadResult.status !== 'queued'" class="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
        <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500">上传状态</h2>
        <div class="mt-3 space-y-2 text-sm text-slate-700">
          <p v-if="uploadResult.status === 'done'" class="text-emerald-600 font-medium">
            ✅ 提取成功！光芒正在汇聚，马上开启你的领地...
          </p>
          <p v-if="uploadResult.status === 'error'" class="text-red-500 font-medium">
            ❌ 提炼失败，可能卷轴封印太强，请重试。
          </p>
        </div>
      </div>

      <p v-if="pollingError" class="mt-4 text-sm font-medium text-red-600">{{ pollingError }}</p>

      <div v-if="rawJobId" class="mt-6 rounded-lg border border-dashed border-slate-300 p-3 text-xs text-slate-500">
        如果自动跳转失败，可手动访问文档路径：
        <span class="font-mono text-slate-700">/documents/{{ Number.parseInt(rawJobId.replace(/-/g, '').slice(0, 8), 16) }}</span>
      </div>
    </div>
  </div>
</template>