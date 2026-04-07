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
      // Keep deterministic seed positions as fallback for malformed data.
      x: 80 + depth * 360,
      y: 60 + idx * 120,
      data: n as unknown as Record<string, unknown>,
    };
  });

  const graphEdges = nodes
    .filter((n) => n.parent_id && idSet.has(n.parent_id))
    .map((n) => ({
      id: `edge:${n.parent_id as string}->${n.node_id}`,
      source: n.parent_id as string,
      target: n.node_id,
    }));

  return { nodes: graphNodes, edges: graphEdges };
}

function resolveClickedNodeId(event: any, nodeIds: string[]): string | null {
  const known = new Set(nodeIds);
  const rawCandidates = [
    event?.itemId,
    event?.data?.id,
    event?.item?.id,
    event?.target?.id,
    event?.target?.config?.id,
    event?.target?.attributes?.id,
  ];

  for (const candidate of rawCandidates) {
    if (typeof candidate !== 'string' || !candidate) {
      continue;
    }
    if (known.has(candidate)) {
      return candidate;
    }
    const matched = nodeIds.find((id) => candidate.includes(id));
    if (matched) {
      return matched;
    }
  }

  return null;
}

function getPartialNodeIds(allNodeIds: string[]): Set<string> {
  const selected = new Set(quizStore.selectedNodeIds);
  const partial = new Set<string>();

  allNodeIds.forEach((id) => {
    if (selected.has(id)) {
      return;
    }
    const descendants = getAllChildIds(id, props.treeData.nodes);
    if (descendants.length === 0) {
      return;
    }
    const selectedCount = descendants.filter((d) => selected.has(d)).length;
    if (selectedCount > 0) {
      partial.add(id);
    }
  });

  return partial;
}

function syncSelectionState(allNodeIds: string[]) {
  if (!graph) {
    return;
  }
  const selected = new Set(quizStore.selectedNodeIds);
  const partial = getPartialNodeIds(allNodeIds);
  const stateMap: Record<string, string[]> = {};

  allNodeIds.forEach((id) => {
    const currentStates = new Set((graph?.getElementState(id) || []) as string[]);
    currentStates.delete('selected');
    currentStates.delete('partial');

    if (selected.has(id)) {
      currentStates.add('selected');
    } else if (partial.has(id)) {
      currentStates.add('partial');
    }

    stateMap[id] = Array.from(currentStates);
  });

  graph.setElementState(stateMap);
}

function setNodeState(nodeId: string, stateName: string, enabled: boolean) {
  if (!graph) {
    return;
  }

  const currentStates = new Set((graph.getElementState(nodeId) || []) as string[]);
  if (enabled) {
    currentStates.add(stateName);
  } else {
    currentStates.delete(stateName);
  }
  graph.setElementState(nodeId, Array.from(currentStates));
}

onMounted(() => {
  if (!containerRef.value) return;

  if (!Array.isArray(props.treeData.nodes)) {
    graphError.value = '知识图数据异常，暂时无法渲染。';
    return;
  }

  const data = buildGraphData(props.treeData.nodes);
  const allNodeIds = props.treeData.nodes.map((n) => n.node_id);
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
      layout: {
        type: 'antv-dagre',
        rankdir: 'LR',
        nodesep: 56,
        ranksep: 180,
      },
      behaviors: ['drag-canvas', 'zoom-canvas'],
      node: {
        type: 'rect',
        style: {
          fill: (d: any) => resolveNodeFill(d),
          size: [260, 62],
          radius: 14,
          padding: 12,
          labelText: (d: any) => d.label,
          labelFill: '#ffffff',
          labelPlacement: 'center',
          labelFontWeight: 'bold',
          labelFontSize: 12,
          labelWordWrap: true,
          labelMaxWidth: 220,
          labelTextOverflow: 'ellipsis',
          cursor: 'pointer',
          shadowColor: (d: any) => resolveNodeFill(d),
          shadowBlur: 10,
          lineWidth: 1,
          stroke: '#c7d2fe',
        },
        state: {
          hover: {
            stroke: '#6366f1',
            lineWidth: 2,
            shadowColor: '#6366f1',
            shadowBlur: 16,
          },
          partial: {
            stroke: '#f59e0b',
            lineWidth: 2,
            shadowColor: '#f59e0b',
            shadowBlur: 14,
          },
          selected: {
            fill: '#10B981',
            stroke: '#047857',
            lineWidth: 2,
            shadowColor: '#10B981',
            shadowBlur: 18,
          }
        }
      },
      edge: {
        type: 'cubic-horizontal',
        style: {
          stroke: '#94a3b8',
          lineWidth: 1.3,
          lineDash: [6, 4],
          endArrow: true,
          opacity: 0.75,
        },
        state: {
          selected: {
            stroke: '#10B981',
            lineWidth: 2,
            shadowColor: '#10B981',
            shadowBlur: 8,
          }
        }
      }
    });

    graph.render();
    syncSelectionState(allNodeIds);
    console.log('[KnowledgeGraph] Graph rendered successfully');

    graph.on('node:mouseenter', (e: any) => {
      const nodeId = resolveClickedNodeId(e, allNodeIds);
      if (!nodeId || !graph) return;
      setNodeState(nodeId, 'hover', true);
    });

    graph.on('node:mouseleave', (e: any) => {
      const nodeId = resolveClickedNodeId(e, allNodeIds);
      if (!nodeId || !graph) return;
      setNodeState(nodeId, 'hover', false);
    });

    graph.on('node:click', (e: any) => {
      const nodeId = resolveClickedNodeId(e, allNodeIds);
      if (!nodeId || !graph) return;

      const selected = new Set(quizStore.selectedNodeIds);
      const isSelected = !selected.has(nodeId);

      // Toggle clicked node
      quizStore.toggleNodeSelection(nodeId, isSelected);

      // Cascade to children
      const childIds = getAllChildIds(nodeId, props.treeData.nodes);
      childIds.forEach(cId => {
        quizStore.toggleNodeSelection(cId, isSelected);
      });

      // Always re-sync the full state to avoid stale visual selection.
      syncSelectionState(allNodeIds);
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
