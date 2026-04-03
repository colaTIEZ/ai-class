import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { initQuiz, type QuestionData } from '../api/quiz';

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
      } else {
        error.value = response.message || 'Failed to generate question';
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'An error occurred';
    } finally {
      isLoading.value = false;
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
    hasQuestion,
    startQuiz,
    resetQuiz,
  };
});
