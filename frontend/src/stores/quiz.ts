import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { initQuiz, submitAnswerStream, type QuestionData, type StreamEvent } from '../api/quiz';

type TracePulse = {
  node_name: string;
  metadata: Record<string, unknown>;
};

function normalizeTracePulse(data: unknown): TracePulse | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const traceData = data as Record<string, unknown>;
  const nodeName = traceData.node_name;
  const metadata =
    traceData.metadata && typeof traceData.metadata === 'object' && !Array.isArray(traceData.metadata)
      ? (traceData.metadata as Record<string, unknown>)
      : {};

  return {
    node_name: String(typeof nodeName === 'string' && nodeName.trim() ? nodeName : 'unknown'),
    metadata,
  };
}

export const useQuizStore = defineStore('quiz', () => {
  // 节点选择状态
  const selectedNodeIds = ref<Set<string>>(new Set());
  const activeDocumentId = ref<number | null>(null);

  // Quiz 问题状态
  const currentQuestion = ref<QuestionData | null>(null);
  const questionType = ref<'multiple_choice' | 'short_answer'>('multiple_choice');
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const traceId = ref<string | null>(null);
  const currentHint = ref<string | null>(null);
  const escapeHatchVisible = ref(false);
  const guardrailReason = ref<string | null>(null);
  const tutorMode = ref<'socratic' | 'semi_transparent'>('socratic');
  const needsReviewQueued = ref(false);
  const isStreaming = ref(false);
  const traceLog = ref<TracePulse[]>([]);
  const currentAnswer = ref('');
  const activeStreamRequestId = ref(0);

  // 计算属性
  const selectedNodeIdsArray = computed(() => Array.from(selectedNodeIds.value));
  const hasSelection = computed(() => selectedNodeIds.value.size > 0);
  const hasQuestion = computed(() => currentQuestion.value !== null);

  function toggleNodeSelection(nodeId: string, isSelected: boolean) {
    if (isSelected) {
      selectedNodeIds.value.add(nodeId);
    } else {
      selectedNodeIds.value.delete(nodeId);
    }
  }

  function clearSelection() {
    selectedNodeIds.value.clear();
  }

  // Ensure selection is cleared when document ID changes (Review Fix)
  function setActiveDocument(docId: number) {
    if (activeDocumentId.value !== docId) {
      activeDocumentId.value = docId;
      clearSelection();
      resetQuiz();
    }
  }

  /**
   * 开始 Quiz - 调用后端 API 生成问题
   */
  async function startQuiz(type: 'multiple_choice' | 'short_answer' = 'multiple_choice') {
    if (!hasSelection.value) {
      error.value = 'Please select at least one topic';
      return;
    }

    isLoading.value = true;
    error.value = null;
    questionType.value = type;

    try {
      const response = await initQuiz({
        selected_node_ids: selectedNodeIdsArray.value,
        question_type: type,
      });

      if (response.status === 'success' && response.data) {
        currentQuestion.value = response.data.question;
        questionType.value = response.data.question_type;
        traceId.value = response.trace_id;
        currentHint.value = null;
        escapeHatchVisible.value = false;
        guardrailReason.value = null;
        tutorMode.value = 'socratic';
        needsReviewQueued.value = false;
        currentAnswer.value = '';
        traceLog.value = [];
      } else {
        error.value = response.message || 'Failed to generate question';
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'An error occurred';
    } finally {
      isLoading.value = false;
    }
  }

  async function submitAnswer(action: 'continue' | 'show_answer' | 'skip' = 'continue') {
    if (!currentQuestion.value) {
      error.value = 'No active question';
      return;
    }
    if (!currentAnswer.value.trim()) {
      error.value = 'Please input your answer';
      return;
    }

    isStreaming.value = true;
    error.value = null;
    currentHint.value = null;
    traceLog.value = [];
    guardrailReason.value = null;
    const requestId = activeStreamRequestId.value + 1;
    activeStreamRequestId.value = requestId;

    try {
      await submitAnswerStream(
        {
          selected_node_ids: selectedNodeIdsArray.value,
          question_type: questionType.value,
          current_question: currentQuestion.value,
          current_answer: currentAnswer.value,
          action,
          current_node_id: currentQuestion.value.current_node_id ?? null,
        },
        (event: StreamEvent) => {
          if (activeStreamRequestId.value !== requestId) {
            return;
          }
          traceId.value = event.trace_id || traceId.value;
          if (event.type === 'content') {
            const text = String(event.data?.text ?? '');
            currentHint.value = text;
            tutorMode.value = (event.data?.tutor_mode as 'socratic' | 'semi_transparent') || tutorMode.value;
            escapeHatchVisible.value = Boolean(event.data?.escape_hatch_visible);
            guardrailReason.value = String(event.data?.guardrail_reason ?? '') || null;
            needsReviewQueued.value = Boolean(event.data?.needs_review_queued);
          } else if (event.type === 'trace') {
            const tracePulse = normalizeTracePulse(event.data);
            if (tracePulse) {
              traceLog.value.push(tracePulse);
            }
          } else if (event.type === 'error') {
            error.value = String(event.data?.message ?? 'Unable to generate hint');
          }
        }
      );
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'An error occurred';
    } finally {
      isStreaming.value = false;
    }
  }

  /**
   * 重置 Quiz 状态
   */
  function resetQuiz() {
    currentQuestion.value = null;
    error.value = null;
    traceId.value = null;
    isLoading.value = false;
    currentHint.value = null;
    escapeHatchVisible.value = false;
    guardrailReason.value = null;
    tutorMode.value = 'socratic';
    needsReviewQueued.value = false;
    isStreaming.value = false;
    traceLog.value = [];
    currentAnswer.value = '';
    activeStreamRequestId.value += 1;
  }

  return {
    // 节点选择
    selectedNodeIds: selectedNodeIdsArray,
    activeDocumentId,
    hasSelection,
    toggleNodeSelection,
    setActiveDocument,
    clearSelection,

    // Quiz 状态
    currentQuestion,
    questionType,
    isLoading,
    error,
    traceId,
    currentHint,
    escapeHatchVisible,
    guardrailReason,
    tutorMode,
    needsReviewQueued,
    isStreaming,
    traceLog,
    currentAnswer,
    hasQuestion,
    startQuiz,
    submitAnswer,
    resetQuiz,
  };
});
