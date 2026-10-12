<script setup>
defineProps({ runs: Array, health: Object });
defineEmits(["resume", "cancel", "focus"]);
const labels = {
  queued: "排队中",
  running: "运行中",
  waiting_selection: "等待选图",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};
</script>
<template>
  <section class="task-panel">
    <div class="panel-title">
      任务记录 <span>{{ runs.length }}</span>
    </div>
    <el-alert
      v-if="!health?.worker"
      title="执行器未就绪，任务将保留在队列中"
      type="warning"
      :closable="false"
    />
    <div v-if="!runs.length" class="task-empty">
      还没有运行记录。<br />连好节点，开始第一次创作。
    </div>
    <article v-for="run in runs" :key="run.id" class="task-card">
      <div class="task-top">
        <span class="task-name">{{ run.step_name }}</span
        ><span :class="['run-badge', run.status]">{{
          labels[run.status]
        }}</span>
      </div>
      <div class="task-detail">
        步骤 {{ Math.min(run.step + 1, run.total_steps) }} /
        {{ run.total_steps }}
        <span>{{
          new Date(run.created_at).toLocaleTimeString("zh-CN", {
            hour: "2-digit",
            minute: "2-digit",
          })
        }}</span>
      </div>
      <div v-if="run.status === 'queued'" class="queue-info">
        队列位置 #{{ run.queue_position ?? "—" }}
      </div>
      <p v-if="run.error" class="task-error">{{ run.error }}</p>
      <div v-if="run.remote_id" class="remote-id">
        远端任务：{{ run.remote_id }}
      </div>
      <div v-if="run.status === 'waiting_selection'" class="waiting-actions">
        <p>选择一张图片，再继续下游步骤。</p>
        <el-button size="small" @click="$emit('focus', run.waiting_result_id)"
          >去选图</el-button
        ><el-button type="primary" size="small" @click="$emit('resume', run.id)"
          >继续</el-button
        >
      </div>
      <el-button
        v-if="['queued', 'waiting_selection'].includes(run.status)"
        link
        size="small"
        class="cancel-button"
        @click="$emit('cancel', run.id)"
        >取消任务</el-button
      >
    </article>
  </section>
</template>
<style scoped>
.task-panel {
  padding: 22px 16px;
}
.panel-title {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}
.panel-title span {
  color: #9aa69d;
  font-weight: 400;
}
.task-empty {
  padding: 55px 8px;
  text-align: center;
  font-size: 12px;
  line-height: 2;
  color: #97a39b;
}
.task-card {
  border: 1px solid #e6ebe7;
  border-radius: 9px;
  padding: 14px;
  margin-top: 12px;
  background: white;
}
.task-top {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  align-items: center;
}
.task-name {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-badge {
  font-size: 10px;
  padding: 3px 6px;
  border-radius: 4px;
  white-space: nowrap;
  background: #f0f4f1;
  color: #65846f;
}
.run-badge.queued,
.run-badge.waiting_selection {
  background: #fff5de;
  color: #a67e32;
}
.run-badge.failed {
  background: #fceeee;
  color: #b85c5c;
}
.run-badge.running {
  background: #e5f3e9;
  color: #2e8b51;
}
.task-detail {
  font-size: 10px;
  display: flex;
  justify-content: space-between;
  color: #98a299;
  margin-top: 12px;
}
.queue-info {
  font-size: 11px;
  margin-top: 12px;
  color: #a2844b;
}
.task-error {
  font-size: 11px;
  color: #c36565;
  line-height: 1.8;
}
.remote-id {
  font-size: 9px;
  color: #a3aca6;
  overflow-wrap: anywhere;
  margin-top: 12px;
}
.waiting-actions p {
  font-size: 11px;
  color: #8d8061;
  line-height: 1.8;
}
.cancel-button {
  margin-top: 12px;
  color: #94a098;
}
</style>
