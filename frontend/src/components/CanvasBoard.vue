<script setup>
import { computed, markRaw, watch, shallowRef, nextTick } from "vue";
import { VueFlow, useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { MiniMap } from "@vue-flow/minimap";
import CanvasNode from "./CanvasNode.vue";
const props = defineProps({
  canvasId: String,
  viewport: Object,
  mode: String,
  loading: Boolean,
  selectedId: String,
});
const nodes = defineModel("nodes", { type: Array }),
  edges = defineModel("edges", { type: Array });
const emit = defineEmits([
  "connect",
  "select",
  "viewport",
  "mode",
  "upload",
  "text",
  "delete",
]);
const nodeTypes = {
  text: markRaw(CanvasNode),
  image: markRaw(CanvasNode),
  workflow: markRaw(CanvasNode),
  result: markRaw(CanvasNode),
};
const { setViewport, screenToFlowCoordinate, findNode, setCenter, fitView } =
  useVueFlow("creative-canvas");
const dropping = shallowRef(false);
const zoom = computed(() => Math.round((props.viewport?.zoom || 1) * 100));
watch(
  () => nodes.value.length,
  async (count, previous) => {
    if (props.loading || count <= previous) return;
    await nextTick();
    await fitView({ padding: 0.15, maxZoom: 1, duration: 200 });
  },
);
watch(
  () => props.canvasId,
  () => {
    if (props.viewport) setViewport(props.viewport);
  },
  { flush: "post" },
);
function initialized() {
  if (props.viewport) setViewport(props.viewport);
}
function drop(event) {
  dropping.value = false;
  emit("upload", {
    files: Array.from(event.dataTransfer.files),
    position: screenToFlowCoordinate({ x: event.clientX, y: event.clientY }),
  });
}
function focusNode(id) {
  const node = findNode(id);
  if (node)
    setCenter(node.position.x + 145, node.position.y + 120, {
      zoom: 1,
      duration: 300,
    });
}
function keydown(event) {
  if (
    !["Delete", "Backspace"].includes(event.key) ||
    event.target.closest("input, textarea, [contenteditable=true]")
  )
    return;
  event.preventDefault();
  emit("delete");
}
defineExpose({ focusNode });
</script>
<template>
  <section
    class="canvas-board"
    :class="{ dropping }"
    tabindex="0"
    @keydown="keydown"
    @dragover.prevent="dropping = true"
    @dragleave.self="dropping = false"
    @drop.prevent="drop"
  >
    <div class="canvas-toolbar">
      <div class="toolbar-left">
        <span class="workspace-label">创作画布</span
        ><span class="toolbar-count">{{ nodes.length }} 个节点</span>
      </div>
      <div class="selection-mode">
        <span>下游选图</span
        ><el-segmented
          :model-value="mode"
          :options="[
            { label: '手动', value: 'manual' },
            { label: '自动', value: 'auto' },
          ]"
          size="small"
          @update:model-value="emit('mode', $event)"
        />
      </div>
    </div>
    <VueFlow
      id="creative-canvas"
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :min-zoom="0.15"
      :max-zoom="2.5"
      :default-viewport="viewport"
      :delete-key-code="null"
      :default-edge-options="{
        type: 'smoothstep',
        style: { stroke: '#85a390', strokeWidth: 1.6 },
      }"
      @init="initialized"
      @connect="emit('connect', $event)"
      @node-click="emit('select', $event.node.id)"
      @pane-click="emit('select', null)"
      @viewport-change-end="emit('viewport', $event)"
    >
      <Background :gap="22" :size="1" pattern-color="#cbd5cd" /><Controls
        :show-interactive="false"
      /><MiniMap
        :pannable="true"
        :zoomable="true"
        :node-color="(n) => (n.type === 'text' ? '#b5aad0' : '#99b8a2')"
      />
    </VueFlow>
    <div v-if="!nodes.length && !loading" class="canvas-welcome">
      <span class="welcome-line">灵感，从这里开始</span>
      <h2>一张画布，无限可能。</h2>
      <p>
        添加文字，连上工作流，生成你的第一张图片。<br />也可以直接把图片拖进来，继续编辑。
      </p>
      <el-button type="primary" plain @click="emit('text')"
        >＋ 添加文字节点</el-button
      >
      <div class="welcome-flow">
        <span>文字</span><i>→</i><span>工作流</span><i>→</i
        ><span>图片结果</span>
      </div>
    </div>
    <div v-if="dropping" class="drop-overlay">松开鼠标，将图片添加到画布</div>
    <div class="canvas-bottom-hint">
      拖动空白处平移 · 滚轮缩放 · Delete 删除 <span>{{ zoom }}%</span
      ><button @click="fitView({ padding: 0.2 })">适应画布</button>
    </div>
    <div v-if="loading" class="board-loading">正在恢复画布…</div>
  </section>
</template>
<style scoped>
.canvas-board {
  position: relative;
  flex: 1;
  min-width: 0;
  background: #f6f8f5;
}
.canvas-toolbar {
  position: absolute;
  top: 18px;
  left: 24px;
  right: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 5;
  pointer-events: none;
}
.toolbar-left,
.selection-mode {
  display: flex;
  align-items: center;
  gap: 13px;
}
.workspace-label {
  font-size: 12px;
  font-weight: 600;
  color: #697d6e;
}
.toolbar-count {
  font-size: 10px;
  color: #a0ada3;
}
.selection-mode {
  pointer-events: auto;
  background: #ffffffeb;
  border: 1px solid #e7ede6;
  padding: 5px 7px 5px 12px;
  border-radius: 7px;
  box-shadow: 0 3px 10px #30452f05;
}
.selection-mode > span {
  font-size: 10px;
  color: #87968c;
}
.canvas-welcome {
  position: absolute;
  left: 50%;
  top: 46%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 4;
  white-space: nowrap;
}
.welcome-line {
  font-size: 10px;
  letter-spacing: 3px;
  color: #9cb0a1;
}
.canvas-welcome h2 {
  font-size: 28px;
  font-weight: 500;
  color: #5f7b67;
  letter-spacing: -1px;
  margin: 20px 0;
}
.canvas-welcome p {
  font-size: 12px;
  color: #9caaa0;
  line-height: 2;
  margin-bottom: 25px;
}
.welcome-flow {
  display: flex;
  gap: 15px;
  align-items: center;
  justify-content: center;
  margin-top: 46px;
  color: #a7b5aa;
  font-size: 10px;
}
.welcome-flow span {
  background: #fdfefd;
  border: 1px solid #e5ebe3;
  border-radius: 5px;
  padding: 7px 14px;
}
.welcome-flow i {
  font-style: normal;
}
.canvas-bottom-hint {
  position: absolute;
  bottom: 25px;
  left: 100px;
  z-index: 5;
  font-size: 9px;
  color: #a1afa4;
  display: flex;
  align-items: center;
  gap: 12px;
}
.canvas-bottom-hint span {
  border-left: 1px solid #dde5dc;
  padding-left: 12px;
}
.canvas-bottom-hint button {
  font-size: 10px;
  color: #8a9f90;
  background: white;
  border: 1px solid #e1e8df;
  border-radius: 4px;
  padding: 5px 8px;
  cursor: pointer;
}
.drop-overlay,
.board-loading {
  position: absolute;
  inset: 0;
  z-index: 9;
  display: grid;
  place-items: center;
  background: #f2f8f0e8;
  font-size: 18px;
  color: #64836b;
}
.dropping {
  outline: 2px dashed #719980;
  outline-offset: -8px;
}
.board-loading {
  font-size: 13px;
}
.canvas-board :deep(.vue-flow__controls) {
  bottom: 18px;
  left: 16px;
  border-radius: 7px;
  overflow: hidden;
  box-shadow: 0 2px 10px #273c2710;
}
.canvas-board :deep(.vue-flow__minimap) {
  width: 130px;
  height: 85px;
  background: #fff;
  border-radius: 7px;
  border: 1px solid #e1e9e0;
  box-shadow: none;
  bottom: 15px;
  right: 15px;
}
.canvas-board :deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #337b4c;
  stroke-width: 3;
}
</style>
