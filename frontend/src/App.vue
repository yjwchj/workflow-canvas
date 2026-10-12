<script setup>
import { onMounted, shallowRef, defineAsyncComponent, h } from "vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { api } from "./api";
import AuthPanel from "./components/AuthPanel.vue";
const Workspace = defineAsyncComponent({
  loader: () => import("./components/Workspace.vue"),
  delay: 200,
  timeout: 30000,
  loadingComponent: {
    render: () => h("div", { class: "app-loading" }, "正在加载画布…"),
  },
  errorComponent: {
    render: () =>
      h("div", { class: "app-loading" }, "画布加载失败，请刷新页面重试"),
  },
});
const user = shallowRef(null);
const loading = shallowRef(true);
onMounted(async () => {
  try {
    user.value = await api("/auth/me");
  } catch {
    /* Login form remains available. */
  } finally {
    loading.value = false;
  }
});
async function logout() {
  await api("/auth/logout", { method: "POST" });
  user.value = null;
}
</script>
<template>
  <el-config-provider :locale="zhCn">
    <div v-if="loading" class="app-loading">正在打开工作台…</div>
    <Workspace v-else-if="user" :user="user" @logout="logout" />
    <AuthPanel v-else @authenticated="user = $event" />
  </el-config-provider>
</template>
