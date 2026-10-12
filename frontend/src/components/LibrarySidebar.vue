<script setup>
import { computed, shallowRef } from "vue";
import {
  EditPen,
  Picture,
  Connection,
  Plus,
  Search,
} from "@element-plus/icons-vue";
const props = defineProps({
  canvases: Array,
  currentId: String,
  templates: Array,
  health: Object,
});
defineEmits(["open", "create", "text", "upload", "workflow"]);
const search = shallowRef("");
const filtered = computed(() =>
  props.templates.filter((t) =>
    t.name.toLowerCase().includes(search.value.toLowerCase()),
  ),
);
</script>
<template>
  <aside class="library-sidebar">
    <div class="library-scroll">
      <div class="sidebar-heading">
        我的画布
        <button title="新建画布" @click="$emit('create')">
          <el-icon><Plus /></el-icon>
        </button>
      </div>
      <button
        v-for="canvas in canvases"
        :key="canvas.id"
        class="canvas-link"
        :class="{ active: canvas.id === currentId }"
        @click="$emit('open', canvas.id)"
      >
        <span class="canvas-symbol">▧</span>{{ canvas.name }}
      </button>
      <div class="library-divider" />
      <div class="sidebar-heading">添加节点 <span>NODE LIBRARY</span></div>
      <div class="basic-nodes">
        <button @click="$emit('text')">
          <el-icon><EditPen /></el-icon><strong>文字</strong
          ><small>写下你的创意</small></button
        ><button @click="$emit('upload')">
          <el-icon><Picture /></el-icon><strong>图片</strong
          ><small>上传本地图片</small>
        </button>
      </div>
      <div class="sidebar-heading workflows-heading">AI 工作流</div>
      <el-input
        v-model="search"
        placeholder="搜索工作流"
        size="small"
        :prefix-icon="Search"
        clearable
      />
      <div v-if="!filtered.length" class="library-empty">
        {{
          templates.length
            ? "没有找到工作流"
            : "还没有可用工作流。\n请维护者在工作流管理中添加模板。"
        }}
      </div>
      <button
        v-for="template in filtered"
        :key="template.id"
        class="workflow-library-card"
        @click="$emit('workflow', template)"
      >
        <div class="workflow-card-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <strong>{{ template.name }}</strong>
        <p>
          {{
            template.kind === "image-edit"
              ? "从已有图片继续编辑"
              : "用文字创造新的画面"
          }}
        </p>
        <div>
          <span class="provider-pill">{{
            template.provider === "comfyui" ? "本地 ComfyUI" : "RunningHub"
          }}</span
          ><span class="add-symbol">＋</span>
        </div>
      </button>
    </div>
    <footer class="library-footer">
      <span class="service-dot" :class="{ online: health?.worker }" />
      <div>
        <strong>{{ health?.worker ? "执行服务已就绪" : "等待执行服务" }}</strong
        ><small>{{
          health?.redis ? "任务队列已连接" : "任务队列未连接"
        }}</small>
      </div>
    </footer>
  </aside>
</template>
<style scoped>
.library-sidebar {
  width: 238px;
  flex-shrink: 0;
  background: white;
  border-right: 1px solid #e6ebe7;
  display: flex;
  flex-direction: column;
}
.library-scroll {
  padding: 24px 18px;
  overflow-y: auto;
  flex: 1;
}
.sidebar-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: #78877d;
  margin-bottom: 14px;
}
.sidebar-heading button {
  border: 0;
  background: none;
  color: #718577;
  cursor: pointer;
}
.sidebar-heading > span {
  font-size: 8px;
  letter-spacing: 1px;
  color: #b0b9b3;
  font-weight: 400;
}
.canvas-link {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 9px;
  border: 0;
  border-radius: 6px;
  background: none;
  padding: 11px;
  color: #7e8a82;
  text-align: left;
  font-size: 12px;
  margin: 3px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.canvas-link.active {
  background: #edf5ee;
  color: #39724a;
  font-weight: 500;
}
.canvas-symbol {
  font-size: 16px;
}
.library-divider {
  height: 1px;
  background: #edf0ee;
  margin: 25px 0;
}
.basic-nodes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.basic-nodes button {
  border: 1px solid #e4eae5;
  border-radius: 8px;
  background: white;
  padding: 14px 8px;
  display: flex;
  align-items: center;
  flex-direction: column;
  cursor: pointer;
}
.basic-nodes button:hover,
.workflow-library-card:hover {
  border-color: #8fb29a;
  background: #fafcf9;
}
.basic-nodes .el-icon {
  font-size: 20px;
  color: #658f72;
  margin-bottom: 10px;
}
.basic-nodes strong {
  font-size: 12px;
  font-weight: 500;
}
.basic-nodes small {
  font-size: 9px;
  color: #a2aca5;
  margin-top: 6px;
}
.workflows-heading {
  margin-top: 30px;
}
.workflow-library-card {
  display: block;
  width: 100%;
  text-align: left;
  background: white;
  border: 1px solid #e3e9e4;
  border-radius: 8px;
  margin-top: 12px;
  padding: 14px;
  cursor: pointer;
}
.workflow-card-icon {
  height: 28px;
  width: 28px;
  border-radius: 7px;
  background: #edf3ee;
  color: #5c8d6d;
  display: grid;
  place-items: center;
  margin-bottom: 13px;
}
.workflow-library-card strong {
  font-size: 12px;
  font-weight: 600;
}
.workflow-library-card p {
  font-size: 10px;
  color: #9ba69f;
  margin: 8px 0 14px;
}
.workflow-library-card > div:last-child {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.provider-pill {
  font-size: 9px;
  color: #819b87;
  border: 1px solid #e1e9e2;
  padding: 3px 5px;
  border-radius: 4px;
}
.add-symbol {
  color: #9aafa0;
}
.library-empty {
  white-space: pre-line;
  font-size: 11px;
  color: #a0aaa3;
  line-height: 1.9;
  margin: 25px 0;
}
.library-footer {
  padding: 20px;
  border-top: 1px solid #e9eeea;
  display: flex;
  gap: 9px;
  align-items: center;
}
.service-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c3b18a;
}
.service-dot.online {
  background: #62a878;
}
.library-footer strong {
  font-size: 10px;
  font-weight: 500;
  display: block;
  color: #7c8b80;
}
.library-footer small {
  font-size: 9px;
  color: #adb5af;
  display: block;
  margin-top: 5px;
}
</style>
