<script setup>
import { ref, reactive, shallowRef, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
const props = defineProps({ open: Boolean });
const emit = defineEmits(["update:open", "updated"]);
const templates = ref([]),
  editing = shallowRef(null),
  busy = shallowRef(false);
const workflowText = shallowRef("{}");
const form = reactive({
  name: "",
  kind: "text-to-image",
  provider: "comfyui",
  enabled: true,
  config: {
    workflow: {},
    workflow_id: "",
    prompt_binding: { node_id: "", field: "text" },
    image_binding: { node_id: "", field: "image" },
    parameters: [],
    output_nodes: [],
  },
});
const outputText = shallowRef("");
const jsonFile = shallowRef(null);
function reset(template) {
  editing.value = template?.id || null;
  const initial = template || {
    name: "",
    kind: "text-to-image",
    provider: "comfyui",
    enabled: true,
    config: {
      workflow: {},
      workflow_id: "",
      prompt_binding: { node_id: "", field: "text" },
      image_binding: { node_id: "", field: "image" },
      parameters: [],
      output_nodes: [],
    },
  };
  Object.assign(form, JSON.parse(JSON.stringify(initial)));
  if (!form.config.image_binding)
    form.config.image_binding = { node_id: "", field: "image" };
  workflowText.value = JSON.stringify(form.config.workflow, null, 2);
  outputText.value = form.config.output_nodes.join(", ");
}
async function load() {
  templates.value = await api("/admin/templates");
}
watch(
  () => props.open,
  async (value) => {
    if (!value) return;
    try {
      await load();
      reset();
    } catch (error) {
      ElMessage.error(error.message);
    }
  },
);
function addParameter() {
  form.config.parameters.push({
    key: "",
    label: "",
    type: "integer",
    default: 1,
    min: null,
    max: null,
    options: [],
    node_id: "",
    field: "",
  });
}
async function readWorkflow(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error("工作流 JSON 请控制在 2 MB 内");
    return;
  }
  try {
    workflowText.value = JSON.stringify(JSON.parse(await file.text()), null, 2);
  } catch {
    ElMessage.error("工作流文件不是有效 JSON");
  }
  event.target.value = "";
}
async function save() {
  busy.value = true;
  try {
    const config = {
      ...form.config,
      workflow:
        form.provider === "comfyui" ? JSON.parse(workflowText.value) : {},
      image_binding:
        form.kind === "image-edit" ? form.config.image_binding : null,
      output_nodes: outputText.value
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      parameters: form.config.parameters.map((p) => ({
        ...p,
        default: ["integer", "number"].includes(p.type)
          ? Number(p.default)
          : String(p.default),
      })),
    };
    await api(`/admin/templates${editing.value ? `/${editing.value}` : ""}`, {
      method: editing.value ? "PUT" : "POST",
      body: {
        name: form.name,
        kind: form.kind,
        provider: form.provider,
        enabled: form.enabled,
        config,
      },
    });
    ElMessage.success("工作流模板已保存");
    await load();
    emit("updated");
    reset();
  } catch (error) {
    ElMessage.error(
      error instanceof SyntaxError ? "工作流 JSON 格式不正确" : error.message,
    );
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <el-dialog
    :model-value="open"
    title="工作流管理"
    width="min(1100px, 94vw)"
    @update:model-value="emit('update:open', $event)"
    ><div class="manager-layout">
      <aside class="template-list">
        <el-button type="primary" plain class="full-width" @click="reset()"
          >＋ 新建模板</el-button
        ><button
          v-for="template in templates"
          :key="template.id"
          class="template-item"
          :class="{ active: editing === template.id }"
          @click="reset(template)"
        >
          <strong>{{ template.name }}</strong
          ><span
            >{{ template.provider }} · v{{ template.version }} ·
            {{ template.enabled ? "已启用" : "已停用" }}</span
          >
        </button>
        <p class="manager-note">
          模板更新不改变已提交任务。旧画布下次运行使用模板最新版本；如参数映射发生变化，请新建模板。
        </p>
      </aside>
      <el-form class="template-form" label-position="top"
        ><div class="form-row">
          <el-form-item label="工作流名称"
            ><el-input
              v-model="form.name"
              placeholder="例如：人像生成 / 图像精修"
              maxlength="100" /></el-form-item
          ><el-form-item label="执行来源"
            ><el-select v-model="form.provider"
              ><el-option label="本地 ComfyUI" value="comfyui" /><el-option
                label="RunningHub"
                value="runninghub" /></el-select
          ></el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="工作流类型"
            ><el-select v-model="form.kind" :disabled="!!editing"
              ><el-option
                label="文字生成图片"
                value="text-to-image" /><el-option
                label="图片编辑"
                value="image-edit" /></el-select></el-form-item
          ><el-form-item label="开放使用"
            ><el-switch v-model="form.enabled" active-text="启用"
          /></el-form-item>
        </div>
        <template v-if="form.provider === 'comfyui'"
          ><el-form-item label="ComfyUI API 格式工作流 JSON"
            ><div class="workflow-json">
              <input
                ref="jsonFile"
                type="file"
                accept=".json"
                hidden
                @change="readWorkflow"
              /><el-button size="small" @click="jsonFile.click()"
                >从文件导入</el-button
              ><el-input
                v-model="workflowText"
                type="textarea"
                :rows="5"
                spellcheck="false"
                placeholder="从 ComfyUI 导出 API 格式工作流"
              /></div></el-form-item
          ><el-form-item
            label="输出节点 ID（可选，逗号分隔；留空保存所有图片输出）"
            ><el-input v-model="outputText" placeholder="9, 15" /></el-form-item
        ></template>
        <el-form-item v-else label="RunningHub 工作流 ID"
          ><el-input
            v-model="form.config.workflow_id"
            placeholder="从 RunningHub 工作流页面复制数字 ID"
          />
          <div class="manager-note">
            API Key 由后端环境变量统一配置，浏览器不保存密钥。
          </div></el-form-item
        >
        <div class="mapping-title">
          输入映射 <span>填写原工作流节点 ID 和输入字段</span>
        </div>
        <div class="mapping-row">
          <strong>文字</strong
          ><el-input
            v-model="form.config.prompt_binding.node_id"
            placeholder="节点 ID，例如 6"
          /><el-input
            v-model="form.config.prompt_binding.field"
            placeholder="字段，例如 text"
          />
        </div>
        <div v-if="form.kind === 'image-edit'" class="mapping-row">
          <strong>图片</strong
          ><el-input
            v-model="form.config.image_binding.node_id"
            placeholder="节点 ID，例如 10"
          /><el-input
            v-model="form.config.image_binding.field"
            placeholder="字段，例如 image"
          />
        </div>
        <div class="mapping-title">
          开放参数
          <el-button link type="primary" @click="addParameter"
            >＋ 添加参数</el-button
          >
        </div>
        <div
          v-for="(parameter, index) in form.config.parameters"
          :key="index"
          class="parameter-card"
        >
          <div class="form-row">
            <el-input
              v-model="parameter.label"
              placeholder="显示名称，例如采样步数"
            /><el-input
              v-model="parameter.key"
              placeholder="参数键，例如 steps"
            />
          </div>
          <div class="form-row">
            <el-select
              v-model="parameter.type"
              @change="
                parameter.default = ['integer', 'number'].includes(
                  parameter.type,
                )
                  ? 1
                  : ''
              "
              ><el-option label="整数" value="integer" /><el-option
                label="小数"
                value="number" /><el-option
                label="文本"
                value="text" /><el-option
                label="选项"
                value="select" /></el-select
            ><el-input v-model="parameter.default" placeholder="默认值" />
          </div>
          <div
            v-if="['integer', 'number'].includes(parameter.type)"
            class="form-row"
          >
            <el-input-number
              v-model="parameter.min"
              placeholder="最小值"
            /><el-input-number v-model="parameter.max" placeholder="最大值" />
          </div>
          <el-input
            v-if="parameter.type === 'select'"
            :model-value="parameter.options.join(',')"
            placeholder="允许选项，用英文逗号分隔"
            @update:model-value="
              parameter.options = $event
                .split(',')
                .map((x) => x.trim())
                .filter(Boolean)
            "
          />
          <div class="form-row">
            <el-input
              v-model="parameter.node_id"
              placeholder="原工作流节点 ID"
            /><el-input
              v-model="parameter.field"
              placeholder="原工作流输入字段"
            />
          </div>
          <el-button
            link
            type="danger"
            @click="form.config.parameters.splice(index, 1)"
            >删除参数</el-button
          >
        </div>
        <p class="manager-note">
          生成次数由画布统一开放（1–8
          次），每次执行工作流保存全部输出图片。若希望每次随机生成，请开放 seed
          参数或在原工作流中配置随机种子节点。
        </p>
        <el-button type="primary" :loading="busy" @click="save">{{
          editing ? "保存新版本" : "创建模板"
        }}</el-button>
      </el-form>
    </div></el-dialog
  >
</template>
<style scoped>
.manager-layout {
  display: grid;
  grid-template-columns: 230px 1fr;
  gap: 28px;
}
.template-list {
  border-right: 1px solid #e7ece8;
  padding-right: 22px;
}
.full-width {
  width: 100%;
}
.template-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  padding: 16px 12px;
  border: 1px solid #e6ece7;
  border-radius: 8px;
  margin-top: 12px;
  background: white;
  text-align: left;
  cursor: pointer;
}
.template-item strong {
  font-size: 13px;
}
.template-item span {
  font-size: 10px;
  color: #88958d;
}
.template-item.active {
  background: #eff6f0;
  border-color: #68a67c;
}
.template-form {
  max-height: 72vh;
  overflow-y: auto;
  padding-right: 10px;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 10px;
}
.form-row .el-form-item {
  margin-bottom: 10px;
}
.workflow-json {
  width: 100%;
}
.workflow-json .el-button {
  margin-bottom: 8px;
}
.mapping-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 24px 0 14px;
  font-size: 13px;
  font-weight: 600;
}
.mapping-title span {
  font-size: 10px;
  font-weight: 400;
  color: #8d9b92;
}
.mapping-row {
  display: grid;
  grid-template-columns: 40px 1fr 1fr;
  gap: 12px;
  align-items: center;
  margin: 10px 0;
  font-size: 12px;
}
.parameter-card {
  border: 1px solid #e1e8e2;
  padding: 14px;
  border-radius: 7px;
  margin-bottom: 12px;
}
.parameter-card > .el-input {
  margin-bottom: 10px;
}
.manager-note {
  font-size: 11px;
  color: #94a098;
  line-height: 1.9;
  margin: 16px 0;
}
.el-input-number {
  width: 100%;
}
@media (max-width: 700px) {
  .manager-layout {
    grid-template-columns: 1fr;
  }
  .template-list {
    border-right: 0;
  }
}
</style>
