<script setup>
import { computed, provide, shallowRef, useTemplateRef } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useCanvas, canvasContext } from "../composables/useCanvas";
import WorkspaceHeader from "./WorkspaceHeader.vue";
import LibrarySidebar from "./LibrarySidebar.vue";
import CanvasBoard from "./CanvasBoard.vue";
import NodeInspector from "./NodeInspector.vue";
import TaskPanel from "./TaskPanel.vue";
import TemplateManager from "./TemplateManager.vue";
import ImageCompare from "./ImageCompare.vue";
const props = defineProps({ user: Object });
const emit = defineEmits(["logout"]);
const canvas = useCanvas();
provide(canvasContext, canvas);
const {
  current,
  canvases,
  templates,
  nodes,
  edges,
  runs,
  health,
  viewport,
  mode,
  saveState,
  loading,
  selectedNode,
  selectedNodeId,
  assetsByNode,
  activeRuns,
} = canvas;
const tab = shallowRef("settings"),
  adminOpen = shallowRef(false),
  compareOpen = shallowRef(false),
  submitting = shallowRef(false);
const fileInput = useTemplateRef("fileInput"),
  board = useTemplateRef("board");
const selectedImages = computed(
  () => assetsByNode.value[selectedNodeId.value] || [],
);
async function safe(action) {
  try {
    await action();
  } catch (error) {
    if (error !== "cancel" && error !== "close")
      ElMessage.error(error.message || "操作失败");
  }
}
async function create() {
  await safe(async () => {
    const { value } = await ElMessageBox.prompt(
      "为新的画布起个名字",
      "新建画布",
      {
        inputValue: "新的创作",
        inputValidator: (value) =>
          (!!value?.trim() && value.length <= 100) ||
          "请输入 1–100 字的画布名称",
      },
    );
    await canvas.create(value.trim());
  });
}
function rename(name) {
  if (current.value) {
    current.value.name = name || "未命名画布";
    canvas.changed();
  }
}
async function run(nodeId) {
  submitting.value = true;
  await safe(() => canvas.run(nodeId));
  submitting.value = false;
  tab.value = "tasks";
}
function focus(id) {
  selectedNodeId.value = id;
  tab.value = "settings";
  board.value?.focusNode(id);
}
async function logout() {
  await safe(async () => {
    await canvas.save();
    emit("logout");
  });
}
</script>
<template>
  <main class="workspace">
    <WorkspaceHeader
      :user="props.user"
      :name="current?.name || ''"
      :save-state="saveState"
      :running="submitting"
      :ready="!!current"
      @rename="rename"
      @save="safe(canvas.save)"
      @run="run(null)"
      @admin="adminOpen = true"
      @export="canvas.exportGraph"
      @logout="logout"
    />
    <div class="workspace-body">
      <LibrarySidebar
        :canvases="canvases"
        :current-id="current?.id"
        :templates="templates"
        :health="health"
        @open="safe(() => canvas.open($event))"
        @create="create"
        @text="canvas.addText()"
        @upload="fileInput.click()"
        @workflow="canvas.addWorkflow"
      /><CanvasBoard
        ref="board"
        v-model:nodes="nodes"
        v-model:edges="edges"
        :canvas-id="current?.id"
        :viewport="viewport"
        :mode="mode"
        :loading="loading"
        :selected-id="selectedNodeId"
        @connect="canvas.connect"
        @select="selectedNodeId = $event"
        @viewport="viewport = $event"
        @mode="mode = $event"
        @text="canvas.addText()"
        @delete="canvas.removeSelected"
        @upload="safe(() => canvas.upload($event.files, $event.position))"
      />
      <aside class="right-panel">
        <div class="panel-tabs">
          <button
            :class="{ active: tab === 'settings' }"
            @click="tab = 'settings'"
          >
            节点设置</button
          ><button :class="{ active: tab === 'tasks' }" @click="tab = 'tasks'">
            任务记录
            <span v-if="activeRuns.length">{{ activeRuns.length }}</span>
          </button>
        </div>
        <div class="panel-scroll">
          <NodeInspector
            v-if="tab === 'settings'"
            :node="selectedNode"
            :templates="templates"
            :images="selectedImages"
            @update="canvas.updateNode(selectedNodeId, $event)"
            @run="run"
            @select="
              canvas.updateNode(selectedNodeId, { selectedAssetId: $event })
            "
            @compare="compareOpen = true"
          /><TaskPanel
            v-else
            :runs="runs"
            :health="health"
            @resume="safe(() => canvas.resume($event))"
            @cancel="safe(() => canvas.cancel($event))"
            @focus="focus"
          />
        </div>
      </aside>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/webp"
      multiple
      hidden
      @change="
        safe(() => canvas.upload(Array.from($event.target.files)));
        $event.target.value = '';
      "
    /><TemplateManager
      v-if="props.user.is_admin"
      v-model:open="adminOpen"
      @updated="safe(canvas.loadTemplates)"
    /><ImageCompare
      v-model:open="compareOpen"
      :images="selectedImages"
      :selected="selectedNode?.data.selectedAssetId"
      @select="canvas.updateNode(selectedNodeId, { selectedAssetId: $event })"
    />
  </main>
</template>
<style scoped>
.workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
  min-width: 950px;
}
.workspace-body {
  display: flex;
  flex: 1;
  min-height: 0;
}
.right-panel {
  width: 280px;
  flex-shrink: 0;
  background: white;
  border-left: 1px solid #e6ebe7;
  display: flex;
  flex-direction: column;
}
.panel-tabs {
  display: flex;
  gap: 22px;
  padding: 0 20px;
  border-bottom: 1px solid #edf1ed;
  height: 53px;
  flex-shrink: 0;
}
.panel-tabs button {
  font-size: 12px;
  border: 0;
  background: none;
  color: #9ba69e;
  padding: 0 0 1px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.panel-tabs button.active {
  color: #457653;
  border-color: #578b65;
}
.panel-tabs span {
  font-size: 9px;
  background: #eff4ef;
  color: #6f8e76;
  padding: 1px 5px;
  border-radius: 9px;
  margin-left: 4px;
}
.panel-scroll {
  flex: 1;
  overflow-y: auto;
}
</style>
