<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '../stores/quiz'
import {
  getChapterMastery,
  getWrongAnswers,
  invalidateQuestionRecord,
  type ChapterMasteryData,
  type ChapterMasteryItem,
  type WrongAnswerNodeGroup,
} from '../api/review'
import { masteryPercent } from '../components/graph/mastery'

const router = useRouter()
const quizStore = useQuizStore()

const isLoading = ref(true)
const errorMessage = ref('')
const wrongAnswerGroups = ref<WrongAnswerNodeGroup[]>([])
const chapterMastery = ref<ChapterMasteryItem[]>([])
const chapterMasterySummary = ref<ChapterMasteryData['summary'] | null>(null)
const invalidatingQuestionIds = ref(new Set<string>())
const reportErrorMessage = ref('')
const activeNodeId = ref<string | null>(null)
const expandedNodeIds = ref(new Set<string>())

const overallMasteryPercent = computed(() => {
  return masteryPercent(chapterMasterySummary.value?.overall_mastery_score)
})

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

// Lightweight 3D Card Hover Effect for Trading Cards
function handleMouseMove(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  const midX = rect.width / 2
  const midY = rect.height / 2
  
  const rotateX = ((y - midY) / midY) * -4
  const rotateY = ((x - midX) / midX) * 4
  
  el.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`
  el.style.boxShadow = '0 20px 40px -10px rgba(79,70,229,0.2)'
}

function handleMouseLeave(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  el.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)'
  el.style.boxShadow = ''
}

async function reportAiError(questionRecordId: string) {
  reportErrorMessage.value = ''
  const nextPending = new Set(invalidatingQuestionIds.value)
  nextPending.add(questionRecordId)
  invalidatingQuestionIds.value = nextPending

  try {
    const response = await invalidateQuestionRecord({
      question_record_id: questionRecordId,
      reason: 'user_reported_ai_error',
    })
    if (response.status !== 'success') {
      return
    }

    wrongAnswerGroups.value = wrongAnswerGroups.value
      .map((group) => {
        const remainingQuestions = group.questions.filter(
          (question) => question.question_record_id !== questionRecordId
        )
        return {
          ...group,
          questions: remainingQuestions,
          total_errors: remainingQuestions.length,
        }
      })
      .filter((group) => group.total_errors > 0)

    if (
      activeNodeId.value &&
      !wrongAnswerGroups.value.some((group) => group.node_id === activeNodeId.value)
    ) {
      activeNodeId.value = null
    }

    try {
      const masteryResp = await getChapterMastery()
      if (masteryResp.status === 'success' && masteryResp.data) {
        chapterMastery.value = masteryResp.data.by_parent
        chapterMasterySummary.value = masteryResp.data.summary
      }
    } catch {
      // Keep review workflow non-blocking when mastery refresh fails.
    }
  } catch (error) {
    reportErrorMessage.value =
      error instanceof Error ? error.message : 'Failed to report AI error. Please try again.'
  } finally {
    const next = new Set(invalidatingQuestionIds.value)
    next.delete(questionRecordId)
    invalidatingQuestionIds.value = next
  }
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
    const wrongAnswerResp = await getWrongAnswers()
    if (wrongAnswerResp.status === 'success' && wrongAnswerResp.data) {
      wrongAnswerGroups.value = wrongAnswerResp.data.by_node
    } else {
      errorMessage.value = wrongAnswerResp.message || 'Failed to load review notebook'
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load review notebook'
  }

  try {
    const masteryResp = await getChapterMastery()
    if (masteryResp.status === 'success' && masteryResp.data) {
      chapterMastery.value = masteryResp.data.by_parent
      chapterMasterySummary.value = masteryResp.data.summary
    }
  } catch {
    chapterMastery.value = []
    chapterMasterySummary.value = null
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
              <h1 class="flex items-center gap-3 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                <span>👾 小怪兽图鉴</span>
              </h1>
              <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                这里收录了你未能击败的知识怪。通过重新挑战（重新作答）来打破封印，夺回丢失的经验值！
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
          <section class="mb-6 rounded-2xl border border-emerald-200/60 bg-emerald-50/70 p-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700">Mastery Snapshot</h2>
                <p class="mt-1 text-sm text-emerald-900">Overall chapter mastery: {{ overallMasteryPercent }}%</p>
              </div>
              <div class="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                {{ chapterMastery.length }} chapters
              </div>
            </div>

            <div v-if="chapterMastery.length" class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="chapter in chapterMastery"
                :key="chapter.parent_id"
                class="rounded-xl border border-emerald-200 bg-white px-3 py-2"
              >
                <div class="truncate text-sm font-semibold text-slate-900">{{ chapter.parent_label }}</div>
                <div class="mt-1 text-xs text-slate-600">{{ masteryPercent(chapter.mastery_score) }}% • {{ chapter.correct_count }}/{{ chapter.attempted_count }}</div>
              </div>
            </div>

            <p v-else class="mt-2 text-sm text-emerald-800">Mastery snapshot unavailable yet</p>
          </section>

          <div v-if="reportErrorMessage" class="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {{ reportErrorMessage }}
          </div>

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

          <div v-else class="space-y-6 perspective-container">
            <article
              v-for="group in visibleGroups"
              :key="group.node_id"
              class="relative overflow-hidden rounded-3xl border-2 border-indigo-100/50 bg-white shadow-sm transition-all duration-200 transform-gpu"
              @mousemove="handleMouseMove"
              @mouseleave="handleMouseLeave"
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
                          class="group relative overflow-hidden rounded-xl bg-orange-500 px-6 py-2.5 text-sm font-bold text-white shadow-[0_0_15px_rgba(249,115,22,0.3)] transition-all hover:bg-orange-400 hover:shadow-[0_0_25px_rgba(249,115,22,0.6)] active:scale-95"
                          @click.stop="retryNode(group.node_id)"
                        >
                          <span class="relative z-10 flex items-center gap-2">⚔️ 打破封印重新挑战</span>
                          <div class="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/30 to-transparent transition-transform duration-500 group-hover:translate-x-full"></div>
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

                      <div class="mt-3 flex justify-end">
                        <button
                          class="report-ai-error rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
                          :disabled="invalidatingQuestionIds.has(question.question_record_id)"
                          @click.stop="reportAiError(question.question_record_id)"
                        >
                          {{ invalidatingQuestionIds.has(question.question_record_id) ? 'Reporting...' : 'Report AI Error/Hallucination' }}
                        </button>
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

.perspective-container {
  perspective: 1000px;
}
</style>
