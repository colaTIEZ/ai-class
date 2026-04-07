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
      // 掌握度刷新失败不阻塞主流程
    }
  } catch (error) {
    reportErrorMessage.value =
      error instanceof Error ? error.message : '由于网络原因报告 AI 错误失败，请重试。'
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
      errorMessage.value = wrongAnswerResp.message || '由于网络原因加载错题回顾失败'
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '由于网络原因加载错题回顾失败'
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
  <div class="review-page min-h-[calc(100vh-4rem)] px-8 py-10">
    <div class="w-full space-y-8">
      <section class="w-full">
        <!-- 头部信息 + 数据卡片 -->
        <div class="flex flex-col gap-6 pb-6 lg:flex-row lg:items-end lg:justify-between" style="border-bottom: 1px solid var(--glass-border);">
          <div class="space-y-3">
            <div class="glass-badge">
              <svg class="w-3.5 h-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              错题记录本
            </div>
            <div>
              <h1 class="text-3xl font-bold tracking-tight sm:text-4xl" style="color: var(--text-heading);">
                错题回顾
              </h1>
              <p class="mt-2 max-w-2xl text-sm leading-6 sm:text-base" style="color: var(--text-muted-on-glass);">
                这里收录了您在测验中答错的题目。通过重新复习和作答来巩固您的知识体系。
              </p>
            </div>
          </div>

          <!-- 数据统计卡片 — 毛玻璃面板 -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:min-w-[380px]">
            <div class="glass-panel px-4 py-3.5">
              <div class="data-label">错题总数</div>
              <div class="data-number mt-1">{{ summary.total_wrong_count }}</div>
            </div>
            <div class="glass-panel px-4 py-3.5">
              <div class="data-label">涉及知识点</div>
              <div class="data-number mt-1">{{ summary.total_nodes_with_errors }}</div>
            </div>
            <button
              class="glass-panel px-4 py-3.5 text-left cursor-pointer transition-all hover:shadow-lg"
              style="background: var(--accent-primary); border-color: rgba(99, 102, 241, 0.3);"
              @click="activeNodeId = null"
            >
              <div class="data-label" style="color: rgba(255,255,255,0.7);">查看</div>
              <div class="mt-1 text-sm font-semibold text-white">显示全部</div>
            </button>
          </div>
        </div>

        <div class="pt-6">
          <!-- 掌握进度快照 — 绿色半透明玻璃 -->
          <section class="glass-card-success mb-6 p-5">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="data-label" style="color: var(--color-success);">掌握进度快照</h2>
                <p class="mt-2 flex items-baseline gap-2">
                  <span class="data-number" style="color: var(--color-success); opacity: 0.7;">{{ overallMasteryPercent }}%</span>
                  <span class="text-sm" style="color: var(--text-muted-on-glass);">整体掌握程度</span>
                </p>
              </div>
              <div class="glass-badge" style="background: var(--color-success-glass); color: var(--color-success); border-color: var(--color-success-border);">
                共 {{ chapterMastery.length }} 个章节
              </div>
            </div>

            <div v-if="chapterMastery.length" class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="chapter in chapterMastery"
                :key="chapter.parent_id"
                class="glass-card px-3.5 py-2.5"
                style="background: rgba(255,255,255,0.6);"
              >
                <div class="truncate text-sm font-semibold" style="color: var(--text-heading);">{{ chapter.parent_label }}</div>
                <div class="mt-1 text-xs" style="color: var(--text-muted-on-glass);">{{ masteryPercent(chapter.mastery_score) }}% · {{ chapter.correct_count }}/{{ chapter.attempted_count }}</div>
              </div>
            </div>

            <p v-else class="mt-3 text-sm" style="color: var(--color-success); opacity: 0.8;">暂无掌握进度快照</p>
          </section>

          <!-- 报告错误提示 -->
          <div v-if="reportErrorMessage" class="glass-card-warning mb-4 px-4 py-3 text-sm" style="color: rgba(146, 64, 14, 0.9);">
            {{ reportErrorMessage }}
          </div>

          <!-- 加载态 -->
          <div v-if="isLoading" class="glass-panel empty-state">
            <div class="glass-spinner mb-3"></div>
            <span class="text-sm font-medium" style="color: var(--text-muted-on-glass);">正在加载错题记录本...</span>
          </div>

          <!-- 错误态 -->
          <div v-else-if="errorMessage" class="glass-card-danger px-4 py-3">
            <span style="color: rgba(185, 28, 28, 0.9);">{{ errorMessage }}</span>
          </div>

          <!-- 空态 -->
          <div v-else-if="visibleGroups.length === 0" class="glass-panel empty-state px-6">
            <svg class="w-12 h-12 mb-4" style="color: var(--text-muted-on-glass); opacity: 0.4;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <p class="text-lg font-semibold" style="color: var(--text-on-glass);">还没有错题记录</p>
            <p class="mt-2 text-sm" style="color: var(--text-muted-on-glass);">完成一些测验后，这里会按知识点自动归类展示。</p>
          </div>

          <!-- 错题分组列表 -->
          <div v-else class="space-y-5">
            <article
              v-for="group in visibleGroups"
              :key="group.node_id"
              class="glass-card relative overflow-hidden"
            >
              <button
                class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left cursor-pointer transition-all"
                style="border-radius: inherit;"
                @click="focusNode(group.node_id)"
              >
                <div class="min-w-0">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold"
                          style="background: var(--color-warning-glass); color: var(--color-warning); border: 1px solid rgba(217, 119, 6, 0.2);">
                      {{ group.questions.length }}
                    </span>
                    <h2 class="truncate text-lg font-bold" style="color: var(--text-heading);">{{ group.node_label }}</h2>
                  </div>
                  <p class="mt-1 text-xs" style="color: var(--text-muted-on-glass); opacity: 0.6;">node_id: {{ group.node_id }}</p>
                </div>

                <div class="flex items-center gap-3">
                  <span class="glass-badge text-xs">
                    {{ expandedNodeIds.has(group.node_id) ? '收起' : '展开' }}
                  </span>
                  <span class="text-xs" style="color: var(--text-muted-on-glass);">{{ activeNodeId === group.node_id ? '取消筛选' : '筛选' }}</span>
                </div>
              </button>

              <transition name="collapse">
                <div v-if="expandedNodeIds.has(group.node_id)" class="px-5 py-5" style="border-top: 1px solid var(--glass-border);">
                  <div class="grid gap-4">
                    <div
                      v-for="question in group.questions"
                      :key="question.question_record_id"
                      class="glass-panel p-4"
                      style="background: var(--glass-bg-card);"
                    >
                      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div class="space-y-3">
                          <p class="data-label">测验原题</p>
                          <p class="text-base leading-7" style="color: var(--text-heading);">{{ question.question_text }}</p>
                          <div class="flex flex-wrap gap-2 text-xs font-medium">
                            <span class="glass-badge" style="background: var(--color-danger-glass); color: var(--color-danger); border-color: rgba(220, 38, 38, 0.15);">{{ question.error_type }}</span>
                            <span class="glass-badge">错误等级 {{ question.error_severity }}</span>
                            <span class="glass-badge" style="background: var(--accent-primary-light); color: var(--accent-primary); border-color: var(--accent-primary-border);">{{ formatDate(question.attempted_at) }}</span>
                          </div>
                        </div>

                        <button
                          class="btn-primary px-5 py-2.5 text-sm flex-shrink-0"
                          @click.stop="retryNode(group.node_id)"
                        >
                          <span class="flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            重新测验
                          </span>
                        </button>
                      </div>

                      <!-- 答案对比 -->
                      <div class="mt-4 grid gap-3 sm:grid-cols-2">
                        <div class="glass-card-danger rounded-xl px-4 py-3">
                          <div class="data-label" style="color: var(--color-danger);">您的答案</div>
                          <div class="mt-1.5 text-sm leading-6 line-through" style="color: rgba(185, 28, 28, 0.85);">{{ question.user_answer }}</div>
                        </div>
                        <div class="glass-card-success rounded-xl px-4 py-3">
                          <div class="data-label" style="color: var(--color-success);">正确答案</div>
                          <div class="mt-1.5 text-sm leading-6" style="color: rgba(4, 120, 87, 0.9);">{{ question.correct_answer }}</div>
                        </div>
                      </div>

                      <!-- AI错误反馈 -->
                      <div class="mt-3 flex justify-end">
                        <button
                          class="glass-btn px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                          :disabled="invalidatingQuestionIds.has(question.question_record_id)"
                          @click.stop="reportAiError(question.question_record_id)"
                        >
                          <span class="flex items-center gap-1.5">
                            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                            {{ invalidatingQuestionIds.has(question.question_record_id) ? '正在报告...' : '反馈 AI 错误/幻觉' }}
                          </span>
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
</style>
