<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { Graph } from '@antv/g6';
import type { KnowledgeTree, KnowledgeNode } from '../../api/documents';
import { useQuizStore } from '../../stores/quiz';
import { masteryBandColor } from './mastery';

const props = defineProps<{
  treeData: KnowledgeTree;
  masteryByParent?: Record<string, number>;
}>();

const containerRef = ref<HTMLElement | null>(null);
const graphError = ref('');
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

// Build plain graph data with deterministic coordinates, avoiding optional layout plugins.
function buildGraphData(nodes: KnowledgeNode[]) {
  const byParent = new Map<string | null, KnowledgeNode[]>();
  const idSet = new Set(nodes.map((n) => n.node_id));

  for (const n of nodes) {
    const parentKey = n.parent_id && idSet.has(n.parent_id) ? n.parent_id : null;
    const bucket = byParent.get(parentKey) ?? [];
    bucket.push(n);
    byParent.set(parentKey, bucket);
  }

  const levels = new Map<string, number>();
  const ordered: KnowledgeNode[] = [];
  const roots = byParent.get(null) ?? [];
  const queue: Array<{ node: KnowledgeNode; depth: number }> = roots.map((node) => ({ node, depth: 0 }));

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) break;
    const { node, depth } = current;
    if (levels.has(node.node_id)) continue;

    levels.set(node.node_id, depth);
    ordered.push(node);

    const children = byParent.get(node.node_id) ?? [];
    for (const child of children) {
      queue.push({ node: child, depth: depth + 1 });
    }
  }

  // Add any disconnected nodes to avoid missing render due to malformed parent links.
  for (const n of nodes) {
    if (!levels.has(n.node_id)) {
      levels.set(n.node_id, 0);
      ordered.push(n);
    }
  }

  const layerIndex = new Map<number, number>();
  const graphNodes = ordered.map((n) => {
    const depth = levels.get(n.node_id) ?? 0;
    const idx = layerIndex.get(depth) ?? 0;
    layerIndex.set(depth, idx + 1);

    return {
      id: n.node_id,
      label: n.label,
      x: 180 + depth * 260,
      y: 120 + idx * 92,
      data: n as unknown as Record<string, unknown>,
    };
  });

  const graphEdges = nodes
    .filter((n) => n.parent_id && idSet.has(n.parent_id))
    .map((n) => ({
      source: n.parent_id as string,
      target: n.node_id,
    }));

  return { nodes: graphNodes, edges: graphEdges };
}

onMounted(() => {
  if (!containerRef.value) return;

  if (!Array.isArray(props.treeData.nodes)) {
    graphError.value = '知识图数据异常，暂时无法渲染。';
    return;
  }

  const data = buildGraphData(props.treeData.nodes);
  console.log('[KnowledgeGraph] Built tree data:', data, 'from', props.treeData.nodes.length, 'nodes');

  if (props.treeData.nodes.length === 0) {
    graphError.value = '暂无知识节点可展示';
    return;
  }

  const resolveNodeFill = (d: any) => {
    const payload = (d?.data ?? {}) as { node_id?: string; parent_id?: string | null };
    const clusterId = payload.parent_id || payload.node_id;
    const score = clusterId ? props.masteryByParent?.[clusterId] : undefined;
    return masteryBandColor(score);
  };

  try {
    graph = new Graph({
      container: containerRef.value,
      autoFit: 'view',
      data,
      behaviors: ['drag-canvas', 'zoom-canvas'],
      node: {
        style: {
          fill: (d: any) => resolveNodeFill(d),
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
    console.log('[KnowledgeGraph] Graph rendered successfully');

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
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    graphError.value = `知识图加载失败: ${message}`;
    console.error('[KnowledgeGraph] Error:', err);
    graph = null;
  }
});

onBeforeUnmount(() => {
  if (graph) {
    graph.destroy();
  }
});
</script>

<template>
  <div class="knowledge-graph-container h-full w-full rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-white">
    <div
      v-if="graphError"
      class="flex h-full min-h-[500px] items-center justify-center px-6 text-center text-sm text-rose-600"
    >
      {{ graphError }}
    </div>
    <div v-else ref="containerRef" class="w-full h-full min-h-[500px]"></div>
  </div>
</template>

<style scoped>
.knowledge-graph-container {
  position: relative;
}
</style>
