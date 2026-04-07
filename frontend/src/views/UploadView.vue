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
  <div class="w-full px-8 py-10">
    <div class="w-full max-w-3xl">
      <!-- 标题区 -->
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center justify-center rounded-xl p-2.5 shadow-sm"
              style="background: var(--accent-primary-light); color: var(--accent-primary);">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </span>
        <h1 class="text-3xl font-bold tracking-tight" style="color: var(--text-heading);">上传学习文档</h1>
      </div>
      <p class="mt-3 text-sm leading-6" style="color: var(--text-muted-on-glass);">
        上传文档 (PDF)，AI 将为您解析内容结构，生成专属的学习图谱和测验。
      </p>

      <!-- 上传卡片 — 独立毛玻璃面板 -->
      <div class="glass-panel mt-8 p-6 transition-all hover:shadow-lg" style="border: 1px solid var(--glass-border-strong);">
        <input
          type="file"
          accept="application/pdf,.pdf"
          @change="onFileChange"
          class="block w-full text-sm cursor-pointer file:mr-4 file:rounded-lg file:border-0 file:px-5 file:py-2.5 file:text-sm file:font-semibold file:cursor-pointer file:transition-all file:duration-200"
          style="color: var(--text-muted-on-glass); --tw-file-bg: rgba(255,255,255,0.6); --tw-file-text: var(--text-on-glass);"
        />
        <p v-if="selectedFile" class="mt-4 inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium glass-card">
          <svg class="w-4 h-4 flex-shrink-0" style="color: var(--accent-primary);" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span style="color: var(--text-on-glass);">文档已就绪: {{ selectedFile.name }} ({{ Math.ceil(selectedFile.size / 1024) }} KB)</span>
        </p>
      </div>

      <!-- 操作按钮区 -->
      <div class="mt-8 flex items-center justify-start gap-4">
        <button
          :disabled="!canUpload"
          @click="() => startUpload()"
          class="btn-primary px-6 py-2.5 text-sm"
        >
          <span class="flex items-center gap-2">
            <svg v-if="!isUploading" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span v-if="!isUploading">开始分析</span>
            <span v-else>处理中...</span>
          </span>
        </button>

        <router-link
          to="/documents"
          class="glass-btn px-5 py-2.5 text-sm"
        >
          返回知识库
        </router-link>
      </div>

      <!-- 重复文件提示 -->
      <div v-if="duplicateDocumentId" class="glass-card-warning mt-4 p-4">
        <p class="text-sm" style="color: rgba(146, 64, 14, 0.9);">
          检测到重复文件，可直接复用已有文档（ID: {{ duplicateDocumentId }})，或强制重新上传。
        </p>
        <div class="mt-3 flex gap-3">
          <button
            @click="reuseExistingDocument"
            class="btn-primary rounded-lg px-4 py-2 text-sm"
            style="background: var(--color-success); box-shadow: 0 4px 14px rgba(5, 150, 105, 0.25);"
          >
            复用已有文档
          </button>
          <button
            :disabled="isUploading"
            @click="startUpload(true)"
            class="glass-btn px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
          >
            强制重新上传
          </button>
        </div>
      </div>

      <p v-if="uploadError" class="mt-4 text-sm font-medium" style="color: var(--color-danger);">{{ uploadError }}</p>

      <!-- 解析中动画 -->
      <div v-if="isPolling" class="mt-10 flex flex-col items-center justify-center pb-6">
        <div class="glass-spinner mb-4"></div>
        <p class="text-sm font-medium" style="color: var(--text-muted-on-glass);">正在提取核心考点... 请稍候</p>
      </div>

      <!-- 处理结果 -->
      <div v-else-if="uploadResult && uploadResult.status !== 'queued'" class="glass-panel mt-8 p-4">
        <div class="space-y-2 text-sm">
          <p v-if="uploadResult.status === 'done'" class="font-medium flex items-center gap-2" style="color: var(--color-success);">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            分析成功！即将为您跳转至知识库...
          </p>
          <p v-if="uploadResult.status === 'error'" class="font-medium flex items-center gap-2" style="color: var(--color-danger);">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            提取失败，请检查文件后重试。
          </p>
        </div>
      </div>

      <p v-if="pollingError" class="mt-4 text-sm font-medium" style="color: var(--color-danger);">{{ pollingError }}</p>

      <!-- 手动跳转提示 -->
      <div v-if="rawJobId" class="glass-card mt-6 p-3 text-xs" style="color: var(--text-muted-on-glass); border-style: dashed;">
        如果自动跳转失败，可手动访问文档路径：
        <span class="font-mono" style="color: var(--text-on-glass);">/documents/{{ Number.parseInt(rawJobId.replace(/-/g, '').slice(0, 8), 16) }}</span>
      </div>
    </div>
  </div>
</template>