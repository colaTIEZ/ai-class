import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useQuizStore = defineStore('quiz', () => {
  const selectedNodeIds = ref<Set<string>>(new Set());
  const activeDocumentId = ref<number | null>(null);

  const selectedNodeIdsArray = computed(() => Array.from(selectedNodeIds.value));
  const hasSelection = computed(() => selectedNodeIds.value.size > 0);

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
    }
  }

  return {
    selectedNodeIds: selectedNodeIdsArray,
    activeDocumentId,
    hasSelection,
    toggleNodeSelection,
    setActiveDocument,
    clearSelection
  };
});
