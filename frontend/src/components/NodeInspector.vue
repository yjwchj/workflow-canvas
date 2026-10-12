<script setup>
import { computed } from "vue";
const props = defineProps({ node: Object, templates: Array, images: Array });
const emit = defineEmits(["update", "run", "select", "compare"]);
const template = computed(() =>
  props.templates.find((t) => t.id === props.node?.data.templateId),
);
function param(key, value) {
  emit("update", { params: { ...props.node.data.params, [key]: value } });
}
const reversedImages = computed(() => [...props.images].reverse());
</script>
<template>
  <div v-if="!node" class="inspector-empty">
    <span class="inspector-glyph">↗</span>
    <h3>选择一个节点</h3>
    <p>在这里调整工作流参数，<br />查看图片和创作历史。</p>
    <div class="inspector-tip">
      拖动节点标题可移动节点<br />从圆点拖线连接输入和输出<br />滚轮缩放 ·
      拖动空白处平移
    </div>
  </div>
  <div v-else class="inspector-content">
    <div class="section-label">节点设置</div>
    <h3 class="inspector-title">{{ node.data.label }}</h3>
    <el-form label-position="top"
      ><el-form-item label="节点名称"
        ><el-input
          :model-value="node.data.label"
          maxlength="100"
          @update:model-value="emit('update', { label: $event })"
      /></el-form-item>
      <el-form-item v-if="node.type === 'text'" label="文字内容"
        ><el-input
          :model-value="node.data.text"
          type="textarea"
          :rows="8"
          maxlength="10000"
          @update:model-value="emit('update', { text: $event })"
      /></el-form-item>
      <template v-if="node.type === 'workflow' && template"
        ><div class="template-description">
          <span>{{
            template.provider === "comfyui" ? "本地 ComfyUI" : "RunningHub"
          }}</span
          ><span>模板 v{{ template.version }}</span>
        </div>
        <el-form-item label="生成次数"
          ><el-input-number
            :model-value="node.data.params.count"
            :min="1"
            :max="8"
            @update:model-value="param('count', $event ?? 1)" /></el-form-item
        ><el-form-item
          v-for="field in template.parameters"
          :key="field.key"
          :label="field.label"
          ><el-input-number
            v-if="['integer', 'number'].includes(field.type)"
            :model-value="node.data.params[field.key] ?? field.default"
            :min="field.min ?? undefined"
            :max="field.max ?? undefined"
            :step="field.type === 'integer' ? 1 : 0.1"
            :precision="field.type === 'integer' ? 0 : undefined"
            @update:model-value="
              param(field.key, $event ?? field.default)
            " /><el-select
            v-else-if="field.type === 'select'"
            :model-value="node.data.params[field.key] ?? field.default"
            @update:model-value="param(field.key, $event)"
            ><el-option
              v-for="option in field.options"
              :key="option"
              :label="option"
              :value="option" /></el-select
          ><el-input
            v-else
            :model-value="node.data.params[field.key] ?? field.default"
            type="textarea"
            :rows="2"
            maxlength="10000"
            @update:model-value="param(field.key, $event)" /></el-form-item
        ><el-button
          type="primary"
          class="full-width"
          @click="emit('run', node.id)"
          >运行此工作流</el-button
        >
        <p class="field-note">每次运行使用独立的参数副本。</p></template
      >
      <el-alert
        v-else-if="node.type === 'workflow'"
        title="模板已停用，请联系维护者"
        type="warning"
        :closable="false"
      />
    </el-form>
    <template v-if="['image', 'result'].includes(node.type)"
      ><div class="history-heading">
        <span>图片历史 · {{ images.length }}</span
        ><el-button
          v-if="images.length > 1"
          link
          type="primary"
          @click="emit('compare')"
          >并排比较</el-button
        >
      </div>
      <div v-if="!images.length" class="no-results">
        还没有图片，运行工作流后自动保存在这里。
      </div>
      <div class="history-grid">
        <button
          v-for="(image, index) in reversedImages"
          :key="image.id"
          class="history-image"
          :class="{ chosen: node.data.selectedAssetId === image.id }"
          @click="emit('select', image.id)"
        >
          <img :src="image.url" alt="历史图片" loading="lazy" /><span
            >{{ images.length - index
            }}<b v-if="node.data.selectedAssetId === image.id">✓</b></span
          >
        </button>
      </div>
      <p v-if="images.length" class="field-note">
        点击图片即可选中。下游每次只使用当前选中的一张图片。
      </p></template
    >
  </div>
</template>
<style scoped>
.inspector-content {
  padding: 24px 20px;
}
.inspector-empty {
  padding: 72px 20px;
  text-align: center;
  color: #98a29b;
}
.inspector-glyph {
  display: block;
  font-size: 36px;
  color: #becbc1;
}
.inspector-empty h3 {
  font-size: 14px;
  color: #69796e;
  margin-top: 22px;
}
.inspector-empty p {
  font-size: 12px;
  line-height: 1.9;
}
.inspector-tip {
  font-size: 11px;
  line-height: 2.2;
  border-top: 1px solid #edf0ed;
  margin-top: 50px;
  padding-top: 22px;
}
.inspector-title {
  font-size: 17px;
  margin: 14px 0 28px;
}
.template-description {
  display: flex;
  justify-content: space-between;
  background: #f0f5f1;
  padding: 12px;
  border-radius: 6px;
  font-size: 11px;
  color: #6b8372;
  margin-bottom: 22px;
}
.field-note {
  font-size: 11px;
  color: #96a39a;
  line-height: 1.8;
}
.full-width {
  width: 100%;
}
.history-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  margin: 25px 0 14px;
}
.history-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.history-image {
  padding: 0;
  border: 2px solid transparent;
  cursor: pointer;
  border-radius: 7px;
  overflow: hidden;
  background: #f3f6f3;
  position: relative;
}
.history-image img {
  width: 100%;
  height: 100px;
  object-fit: contain;
  display: block;
}
.history-image span {
  display: flex;
  justify-content: space-between;
  padding: 6px 9px;
  font-size: 11px;
  color: #819087;
}
.history-image.chosen {
  border-color: #4a9066;
}
.history-image b {
  color: #3c8559;
}
.no-results {
  font-size: 12px;
  color: #95a099;
  line-height: 1.8;
}
</style>
