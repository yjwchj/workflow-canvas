<script setup>
defineProps({
  user: Object,
  name: String,
  saveState: String,
  running: Boolean,
  ready: Boolean,
});
defineEmits(["rename", "save", "run", "admin", "logout", "export"]);
</script>
<template>
  <header class="workspace-header">
    <div class="brand">
      <span class="brand-icon">织</span> 织图 <small>FLOW CANVAS</small>
    </div>
    <div class="header-center">
      <el-input
        class="canvas-name"
        :model-value="name"
        maxlength="100"
        @update:model-value="$emit('rename', $event)"
      /><span class="header-divider" /><button
        class="save-status"
        @click="$emit('save')"
      >
        <span :class="{ unsaved: saveState !== '已保存' }">●</span
        >{{ saveState }}
      </button>
    </div>
    <div class="header-actions">
      <el-button v-if="user.is_admin" text @click="$emit('admin')"
        >工作流管理</el-button
      ><el-button text :disabled="!ready" @click="$emit('export')"
        >导出</el-button
      ><el-button
        type="primary"
        :loading="running"
        :disabled="!ready"
        @click="$emit('run')"
        >▶ 运行流程</el-button
      ><el-dropdown @command="$emit('logout')"
        ><div class="user-avatar" :title="user.username">
          {{ user.username.slice(0, 1).toUpperCase() }}
        </div>
        <template #dropdown
          ><el-dropdown-menu
            ><el-dropdown-item disabled>{{ user.username }}</el-dropdown-item
            ><el-dropdown-item divided command="logout"
              >退出登录</el-dropdown-item
            ></el-dropdown-menu
          ></template
        ></el-dropdown
      >
    </div>
  </header>
</template>
<style scoped>
.workspace-header {
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 25px;
  background: white;
  border-bottom: 1px solid #e7ece8;
}
.header-center {
  display: flex;
  align-items: center;
  gap: 15px;
  flex: 1;
  margin-left: 48px;
}
.canvas-name {
  width: 180px;
}
.canvas-name :deep(.el-input__wrapper) {
  box-shadow: none;
  font-weight: 600;
}
.header-divider {
  height: 18px;
  width: 1px;
  background: #e2e8e3;
}
.save-status {
  border: 0;
  background: none;
  font-size: 11px;
  white-space: nowrap;
  color: #9aa59d;
  cursor: pointer;
}
.save-status span {
  color: #5a9f71;
  margin-right: 7px;
  font-size: 8px;
}
.save-status .unsaved {
  color: #ccaa63;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #e9efe9;
  color: #5d7d65;
  font-size: 12px;
  cursor: pointer;
  margin-left: 10px;
}
@media (max-width: 1100px) {
  .brand small {
    display: none;
  }
  .header-center {
    margin-left: 0;
  }
  .canvas-name {
    width: 140px;
  }
  .header-actions {
    gap: 2px;
  }
  .workspace-header {
    padding: 0 15px;
    gap: 10px;
  }
  .save-status {
    max-width: 130px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
</style>
