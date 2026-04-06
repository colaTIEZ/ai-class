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
    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 class="text-2xl font-bold text-slate-800">上传 PDF</h1>
      <p class="mt-2 text-sm text-slate-600">
        仅支持 PDF，大小不超过 10MB。上传后会进入队列并自动轮询处理进度。
      </p>

      <div class="mt-6">
        <input
          type="file"
          accept="application/pdf,.pdf"
          @change="onFileChange"
          class="block w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm"
        />
        <p v-if="selectedFile" class="mt-2 text-sm text-slate-500">
          已选择: {{ selectedFile.name }} ({{ Math.ceil(selectedFile.size / 1024) }} KB)
        </p>
      </div>

      <div class="mt-6 flex gap-3">
        <button
          :disabled="!canUpload"
          @click="() => startUpload()"
          class="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {{ isUploading ? '上传中...' : '开始上传' }}
        </button>

        <router-link
          to="/documents"
          class="rounded-md border border-slate-300 px-5 py-2.5 text-sm text-slate-700 transition hover:bg-slate-50"
        >
          去文档页
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

      <div v-if="uploadResult" class="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h2 class="text-sm font-semibold text-slate-700">上传状态</h2>
        <div class="mt-3 space-y-1 text-sm text-slate-700">
          <p><span class="font-medium">Job ID:</span> {{ uploadResult.job_id }}</p>
          <p><span class="font-medium">状态:</span> {{ uploadResult.status }}</p>
          <p v-if="uploadResult.status === 'queued'">
            <span class="font-medium">队列位置:</span> {{ uploadResult.position }}
          </p>
          <p v-if="isPolling" class="text-indigo-600">正在轮询处理状态...</p>
          <p v-if="uploadResult.status === 'done'" class="text-green-600">
            处理完成，正在跳转到文档页。
          </p>
          <p v-if="uploadResult.status === 'error'" class="text-red-600">
            处理失败，请重新上传。
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