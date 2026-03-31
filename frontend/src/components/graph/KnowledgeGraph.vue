<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { Graph } from '@antv/g6';
import type { KnowledgeTree, KnowledgeNode } from '../../api/documents';
import { useQuizStore } from '../../stores/quiz';

const props = defineProps<{
  treeData: KnowledgeTree;
}>();

const containerRef = ref<HTMLElement | null>(null);
let graph: Graph | null = null;
const quizStore = useQuizStore();

/**
 * Recursively find all child Node IDs given a starting Node ID.
 * Includes infinite recursion protection.
 */
function getAllChildIds(startNodeId: string, nodes: KnowledgeNode[]): string[] {
  const result: string[] = [];
  const visited = new Set<string>();
  
  const findChildren = (parentId: string) => {
    if (visited.has(parentId)) return;
    visited.add(parentId);

    const children = nodes.filter(n => n.parent_id === parentId);
    for (const c of children) {
      result.push(c.node_id);
      findChildren(c.node_id);
    }
  };
  findChildren(startNodeId);
  return result;
}

// Convert flat data to tree structure expected by AntV G6
function buildTreeData(nodes: KnowledgeNode[]) {
  const nodeMap = new Map<string, any>();
  const roots: any[] = [];

  nodes.forEach(n => {
    nodeMap.set(n.node_id, {
      id: n.node_id,
      label: n.label,
      children: [],
      data: n
    });
  });

  nodes.forEach(n => {
    const gn = nodeMap.get(n.node_id);
    if (n.parent_id === null || !nodeMap.has(n.parent_id)) {
      roots.push(gn);
    } else {
      const parent = nodeMap.get(n.parent_id);
      parent.children.push(gn);
    }
  });

  if (roots.length > 1) {
    return {
      id: 'root-container',
      label: 'Course Outline',
      children: roots
    };
  }

  return roots[0] || { id: 'empty', label: 'No Data' };
}

onMounted(() => {
  if (!containerRef.value) return;

  const data = buildTreeData(props.treeData.nodes);

  graph = new Graph({
    container: containerRef.value,
    autoFit: 'view',
    data,
    layout: {
      type: 'compactBox',
      direction: 'LR',
      preventOverlap: true,
      nodeSep: 50,
      rankSep: 100,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'collapse-expand'],
    node: {
      style: {
        fill: '#4F46E5',
        radius: 4,
        padding: 6,
        labelText: (d: any) => d.label,
        labelFill: '#ffffff',
        labelPlacement: 'center',
        cursor: 'pointer',
      },
      state: {
        selected: {
          fill: '#10B981',
          stroke: '#047857',
          lineWidth: 2,
        }
      }
    },
    edge: {
      style: {
        stroke: '#cbd5e1',
        lineWidth: 1,
      }
    }
  });

  graph.render();

  graph.on('node:click', (e: any) => {
    // Determine node ID from the event (Targeted fix for G6 v5)
    const nodeId = e.target?.id || e.itemId || e.item?.id;
    if (!nodeId || !graph) return;

    const isSelected = !quizStore.selectedNodeIds.includes(nodeId);
    
    // Toggle clicked node
    quizStore.toggleNodeSelection(nodeId, isSelected);
    graph.setElementState(nodeId, 'selected', isSelected);

    // Cascade to children
    const childIds = getAllChildIds(nodeId, props.treeData.nodes);
    childIds.forEach(cId => {
      quizStore.toggleNodeSelection(cId, isSelected);
      graph?.setElementState(cId, 'selected', isSelected);
    });
  });
});

onBeforeUnmount(() => {
  if (graph) {
    graph.destroy();
  }
});
</script>

<template>
  <div class="knowledge-graph-container h-full w-full rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-white">
    <div ref="containerRef" class="w-full h-full min-h-[500px]"></div>
  </div>
</template>

<style scoped>
.knowledge-graph-container {
  position: relative;
}
</style>
