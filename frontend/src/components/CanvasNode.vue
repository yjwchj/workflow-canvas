<script setup>
import { computed, inject } from "vue";
import { ElMessage } from "element-plus";
import { Handle, Position } from "@vue-flow/core";
import {
  Picture,
  EditPen,
  Connection,
  MoreFilled,
} from "@element-plus/icons-vue";
import { canvasContext } from "../composables/useCanvas";
const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean,
});
const canvas = inject(canvasContext);
const images = computed(() => canvas.assetsByNode.value[props.id] || []);
const selectedImage = computed(
  () =>
    images.value.find((a) => a.id === props.data.selectedAssetId) ||
    images.value.at(-1),
);
const template = computed(() =>
  canvas.templates.value.find((t) => t.id === props.data.templateId),
);
const nodeRun = computed(() =>
  canvas.runs.value.find(
    (r) =>
      r.node_id === props.id &&
      ["queued", "running", "failed"].includes(r.status),
  ),
);
const statusLabels = { queued: "排队中", running: "运行中", failed: "失败" };
const number = computed(
  () => images.value.findIndex((a) => a.id === selectedImage.value?.id) + 1,
);
function cycle(direction) {
  const index =
    (number.value - 1 + direction + images.value.length) % images.value.length;
  canvas.updateNode(props.id, { selectedAssetId: images.value[index].id });
}
async function run() {
  try {
    await canvas.run(props.id);
  } catch (error) {
    ElMessage.error(error.message);
  }
}
</script>
<template>
  <article class="canvas-node" :class="[type, { 'is-selected': selected }]">
    <header class="node-header">
      <span class="node-kind"
        ><el-icon
          ><EditPen v-if="type === 'text'" /><Connection
            v-else-if="type === 'workflow'" /><Picture v-else /></el-icon
        >{{ data.label }}</span
      ><span class="node-dot">•••</span>
    </header>
    <div v-if="type === 'text'" class="node-body">
      <el-input
        class="nodrag nopan"
        :model-value="data.text"
        type="textarea"
        :rows="5"
        placeholder="描述你想看见的画面…"
        maxlength="10000"
        @update:model-value="canvas.updateNode(id, { text: $event })"
      />
      <div class="port-caption right">文字输出 <i class="text-dot" /></div>
    </div>
    <div v-else-if="type === 'workflow'" class="node-body">
      <div class="provider-label">
        {{ template?.provider === "runninghub" ? "RUNNINGHUB" : "COMFYUI" }}
        <span>{{ template ? `v${template.version}` : "模板已停用" }}</span>
      </div>
      <p class="workflow-desc">
        {{
          template?.kind === "image-edit"
            ? "从选中的图片继续创作"
            : "将你的文字变成一张图片"
        }}
      </p>
      <div class="workflow-ports">
        <span><i class="text-dot" /> 文字输入</span
        ><span v-if="template?.kind === 'image-edit'"
          ><i class="image-dot" /> 图片输入</span
        >
      </div>
      <div class="workflow-bottom">
        <span :class="['task-status', nodeRun?.status]">{{
          statusLabels[nodeRun?.status] || "等待运行"
        }}</span
        ><el-button
          size="small"
          class="nodrag nopan"
          type="primary"
          plain
          :disabled="
            !template || ['queued', 'running'].includes(nodeRun?.status)
          "
          @click="run"
          >运行</el-button
        >
      </div>
    </div>
    <div v-else class="node-body image-body">
      <div
        class="image-preview nodrag nopan"
        @click="canvas.selectedNodeId.value = id"
      >
        <img v-if="selectedImage" :src="selectedImage.url" :alt="data.label" />
        <div v-else class="image-placeholder">
          <el-icon :size="32"><Picture /></el-icon
          ><span>{{
            type === "result"
              ? "运行工作流后，图片会出现在这里"
              : "上传的图片会出现在这里"
          }}</span>
        </div>
      </div>
      <div class="image-footer nodrag nopan">
        <span>{{
          images.length ? `已选择 ${number} / ${images.length}` : "暂无图片"
        }}</span>
        <div v-if="images.length > 1">
          <button aria-label="上一张图片" @click="cycle(-1)">‹</button
          ><button aria-label="下一张图片" @click="cycle(1)">›</button>
        </div>
      </div>
      <div v-if="images.length" class="image-meta">
        {{ selectedImage.width }} × {{ selectedImage.height }}
        <span>点击节点查看历史</span>
      </div>
    </div>
    <Handle
      v-if="type === 'text'"
      id="text"
      type="source"
      :position="Position.Right"
      class="text-handle"
    />
    <Handle
      v-if="type === 'workflow'"
      id="text"
      type="target"
      :position="Position.Left"
      :style="{ top: '51%' }"
      class="text-handle"
    />
    <Handle
      v-if="type === 'workflow' && template?.kind === 'image-edit'"
      id="image"
      type="target"
      :position="Position.Left"
      :style="{ top: '66%' }"
      class="image-handle"
    />
    <Handle
      v-if="type === 'workflow'"
      id="image"
      type="source"
      :position="Position.Right"
      class="image-handle"
    />
    <Handle
      v-if="type === 'result'"
      id="image"
      type="target"
      :position="Position.Left"
      class="image-handle"
    />
    <Handle
      v-if="['image', 'result'].includes(type)"
      id="image"
      type="source"
      :position="Position.Right"
      class="image-handle"
    />
  </article>
</template>
<style scoped>
.canvas-node {
  width: 290px;
  background: white;
  border: 1px solid #dfe5e0;
  border-radius: 12px;
  box-shadow: 0 4px 16px #223d2810;
}
.is-selected {
  border-color: #448c63;
  box-shadow: 0 0 0 2px #448c6320;
}
.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #eef1ee;
  cursor: grab;
  font-size: 13px;
  font-weight: 600;
}
.node-kind {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 240px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.node-kind .el-icon {
  color: #4f8764;
}
.node-dot {
  color: #a4afa7;
  letter-spacing: 2px;
}
.node-body {
  padding: 16px;
}
.port-caption {
  font-size: 11px;
  color: #86908a;
  margin-top: 14px;
}
.right {
  text-align: right;
}
.text-dot,
.image-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin: 0 4px;
  background: #a18fd1;
}
.image-dot {
  background: #4eaa7b;
}
.provider-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #658471;
  display: flex;
  justify-content: space-between;
}
.provider-label span {
  color: #9ba79f;
}
.workflow-desc {
  font-size: 13px;
  margin: 14px 0;
  color: #7c8780;
}
.workflow-ports {
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #7e8a82;
  margin: 20px 0;
}
.workflow-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #eff2ef;
  padding-top: 14px;
}
.task-status {
  font-size: 11px;
  color: #969f99;
}
.running {
  color: #3a8c5a;
}
.queued {
  color: #bc9746;
}
.failed {
  color: #c86464;
}
.image-preview {
  height: 190px;
  background: #f3f5f3;
  border-radius: 6px;
  display: grid;
  place-items: center;
  overflow: hidden;
  cursor: pointer;
}
.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: #a2b0a6;
  font-size: 10px;
}
.image-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  font-size: 11px;
  color: #69786e;
}
.image-footer button {
  border: 1px solid #e2e7e2;
  background: white;
  border-radius: 4px;
  margin-left: 5px;
  padding: 0 9px;
  cursor: pointer;
  font-size: 17px;
}
.image-meta {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #a0aaa3;
  margin-top: 8px;
}
.text-handle {
  background: #a18fd1 !important;
}
.image-handle {
  background: #4eaa7b !important;
}
.vue-flow__handle {
  width: 10px;
  height: 10px;
  border: 2px solid white;
  box-shadow: 0 0 0 1px #d9e0db;
}
</style>
