<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '../stores/quiz'
import { getWrongAnswers, type WrongAnswerNodeGroup } from '../api/review'

const router = useRouter()
const quizStore = useQuizStore()

const isLoading = ref(true)
const errorMessage = ref('')
const wrongAnswerGroups = ref<WrongAnswerNodeGroup[]>([])
const activeNodeId = ref<string | null>(null)
const expandedNodeIds = ref(new Set<string>())

const summary = computed(() => ({
  total_wrong_count: wrongAnswerGroups.value.reduce((sum, group) => sum + group.total_errors, 0),
  total_nodes_with_errors: wrongAnswerGroups.value.length,
}))

const visibleGroups = computed(() => {
  if (!activeNodeId.value) {
    return wrongAnswerGroups.value
  }

  return wrongAnswerGroups.value.filter((group) => group.node_id === activeNodeId.value)
})

function toggleNodeExpansion(nodeId: string) {
  const next = new Set(expandedNodeIds.value)
  if (next.has(nodeId)) {
    next.delete(nodeId)
  } else {
    next.add(nodeId)
  }
  expandedNodeIds.value = next
}

function focusNode(nodeId: string) {
  activeNodeId.value = activeNodeId.value === nodeId ? null : nodeId
  toggleNodeExpansion(nodeId)
}

function retryNode(nodeId: string) {
  quizStore.clearSelection()
  quizStore.toggleNodeSelection(nodeId, true)
  router.push('/quiz')
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    const response = await getWrongAnswers()
    if (response.status === 'success' && response.data) {
      wrongAnswerGroups.value = response.data.by_node
    } else {
      errorMessage.value = response.message || 'Failed to load review notebook'
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load review notebook'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="review-page min-h-[calc(100vh-4rem)] bg-[radial-gradient(circle_at_top,_#f8fafc,_#eef2ff_45%,_#e2e8f0_100%)] px-4 py-8 sm:px-6 lg:px-10">
    <div class="mx-auto max-w-6xl space-y-8">
      <section class="overflow-hidden rounded-3xl border border-slate-200/80 bg-white/85 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
        <div class="flex flex-col gap-6 border-b border-slate-100 px-6 py-6 sm:px-8 lg:flex-row lg:items-end lg:justify-between">
          <div class="space-y-3">
            <div class="inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
              Wrong-Answer Notebook
            </div>
            <div>
              <h1 class="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                按知识点回看错题
              </h1>
              <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                所有错误按 node_id 分组，方便你快速定位系统性薄弱点，并从当前知识点重新开练。
              </p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:min-w-[360px]">
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div class="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Wrong</div>
              <div class="mt-1 text-2xl font-black text-slate-900">{{ summary.total_wrong_count }}</div>
            </div>
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div class="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Nodes</div>
              <div class="mt-1 text-2xl font-black text-slate-900">{{ summary.total_nodes_with_errors }}</div>
            </div>
            <button
              class="rounded-2xl border border-indigo-200 bg-indigo-600 px-4 py-3 text-left text-white transition hover:bg-indigo-500"
              @click="activeNodeId = null"
            >
              <div class="text-xs font-medium uppercase tracking-[0.18em] text-indigo-100">View</div>
              <div class="mt-1 text-sm font-semibold">Show all nodes</div>
            </button>
          </div>
        </div>

        <div class="px-6 py-6 sm:px-8">
          <div v-if="isLoading" class="flex min-h-[18rem] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-slate-500">
            Loading wrong-answer notebook...
          </div>

          <div v-else-if="errorMessage" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {{ errorMessage }}
          </div>

          <div v-else-if="visibleGroups.length === 0" class="flex min-h-[18rem] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-slate-500">
            <p class="text-lg font-semibold text-slate-700">还没有错题记录</p>
            <p class="mt-2 text-sm text-slate-500">完成一些测验后，这里会按知识点自动归类展示。</p>
          </div>

          <div v-else class="space-y-4">
            <article
              v-for="group in visibleGroups"
              :key="group.node_id"
              class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md"
            >
              <button
                class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
                @click="focusNode(group.node_id)"
              >
                <div class="min-w-0">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-700">
                      {{ group.questions.length }}
                    </span>
                    <h2 class="truncate text-lg font-bold text-slate-900">{{ group.node_label }}</h2>
                  </div>
                  <p class="mt-1 text-sm text-slate-500">node_id: {{ group.node_id }}</p>
                </div>

                <div class="flex items-center gap-3">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
                    {{ expandedNodeIds.has(group.node_id) ? 'Expanded' : 'Collapsed' }}
                  </span>
                  <span class="text-slate-400">{{ activeNodeId === group.node_id ? 'Filtered' : 'Filter' }}</span>
                </div>
              </button>

              <transition name="collapse">
                <div v-if="expandedNodeIds.has(group.node_id)" class="border-t border-slate-100 px-5 py-5">
                  <div class="grid gap-4">
                    <div
                      v-for="question in group.questions"
                      :key="question.question_record_id"
                      class="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                    >
                      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div class="space-y-3">
                          <p class="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Question</p>
                          <p class="text-base leading-7 text-slate-900">{{ question.question_text }}</p>
                          <div class="flex flex-wrap gap-2 text-xs font-medium">
                            <span class="rounded-full bg-red-100 px-2.5 py-1 text-red-700">{{ question.error_type }}</span>
                            <span class="rounded-full bg-slate-200 px-2.5 py-1 text-slate-700">Severity {{ question.error_severity }}</span>
                            <span class="rounded-full bg-indigo-100 px-2.5 py-1 text-indigo-700">{{ formatDate(question.attempted_at) }}</span>
                          </div>
                        </div>

                        <button
                          class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                          @click.stop="retryNode(group.node_id)"
                        >
                          重新作答
                        </button>
                      </div>

                      <div class="mt-4 grid gap-3 sm:grid-cols-2">
                        <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
                          <div class="text-xs font-semibold uppercase tracking-[0.16em] text-red-600">Your answer</div>
                          <div class="mt-1 text-sm leading-6 text-red-900 line-through">{{ question.user_answer }}</div>
                        </div>
                        <div class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                          <div class="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-600">Correct answer</div>
                          <div class="mt-1 text-sm leading-6 text-emerald-900">{{ question.correct_answer }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </transition>
            </article>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.22s ease;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  transform: translateY(-4px);
  max-height: 0;
}
</style>
