import { createApp } from "vue";
import {
  ElAlert,
  ElButton,
  ElConfigProvider,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSegmented,
  ElSelect,
  ElSwitch,
} from "element-plus";
import "element-plus/dist/index.css";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";
import "@vue-flow/minimap/dist/style.css";
import "./style.css";
import App from "./App.vue";
const app = createApp(App);
for (const component of [
  ElAlert,
  ElButton,
  ElConfigProvider,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSegmented,
  ElSelect,
  ElSwitch,
]) {
  app.component(component.name, component);
}
app.mount("#app");
