<script setup>
import { reactive, shallowRef } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
const emit = defineEmits(["authenticated"]);
const form = reactive({ username: "", password: "" });
const register = shallowRef(false);
const busy = shallowRef(false);
async function submit() {
  if (
    !/^[a-zA-Z0-9_-]{3,40}$/.test(form.username) ||
    form.password.length < 8
  ) {
    ElMessage.warning(
      "用户名需为 3–40 位英文、数字、下划线或短横线，密码至少 8 位",
    );
    return;
  }
  busy.value = true;
  try {
    emit(
      "authenticated",
      await api(`/auth/${register.value ? "register" : "login"}`, {
        method: "POST",
        body: form,
      }),
    );
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <main class="auth-page">
    <section class="auth-story">
      <div class="brand">
        <span class="brand-icon">织</span> 织图 <small>FLOW CANVAS</small>
      </div>
      <div class="story-body">
        <span class="eyebrow">让想法，自由生长</span>
        <h1>把灵感连起来。<br />让创作留在画布上。</h1>
        <p>
          文字生成、选图比较、继续编辑。<br />你和朋友的创作，各有自己的空间。
        </p>
        <div class="flow-illustration">
          <div>文字灵感 <span>→</span></div>
          <div class="illustration-primary">AI 工作流 <span>→</span></div>
          <div>新的作品</div>
        </div>
      </div>
      <div class="story-footer">
        局域网创作工作台 <span>COMFYUI · RUNNINGHUB</span>
      </div>
    </section>
    <section class="auth-form">
      <div class="auth-card">
        <span class="eyebrow">你的创作空间</span>
        <h2>{{ register ? "创建账号" : "欢迎回来" }}</h2>
        <p>登录后恢复你的画布、参数和图片历史。</p>
        <el-form label-position="top" @submit.prevent="submit"
          ><el-form-item label="用户名"
            ><el-input
              v-model="form.username"
              placeholder="英文、数字、下划线或短横线"
              autocomplete="username"
              maxlength="40" /></el-form-item
          ><el-form-item label="密码"
            ><el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="至少 8 位"
              :autocomplete="register ? 'new-password' : 'current-password'"
              maxlength="128" /></el-form-item
          ><el-button
            class="auth-submit"
            type="primary"
            native-type="submit"
            :loading="busy"
            >{{ register ? "注册并进入画布" : "进入工作台" }}</el-button
          ></el-form
        >
        <div class="auth-switch">
          {{ register ? "已有账号？" : "第一次使用？"
          }}<el-button link type="primary" @click="register = !register">{{
            register ? "登录" : "创建账号"
          }}</el-button>
        </div>
        <div class="auth-note">账号之间的画布、任务和图片独立保存。</div>
      </div>
    </section>
  </main>
</template>
<style scoped>
.auth-page {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  min-height: 100vh;
}
.auth-story {
  background: #eaf0ec;
  padding: 40px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.story-body {
  max-width: 640px;
  margin: 70px 0;
}
.story-body h1 {
  font-size: clamp(32px, 3.5vw, 54px);
  line-height: 1.4;
  font-weight: 600;
  letter-spacing: -2px;
  margin: 24px 0;
}
.story-body p {
  line-height: 2;
  color: #68766e;
}
.flow-illustration {
  display: flex;
  gap: 12px;
  margin-top: 54px;
}
.flow-illustration > div {
  border: 1px solid #c7d6cb;
  border-radius: 12px;
  padding: 20px;
  background: #f5f8f5;
  font-size: 14px;
}
.flow-illustration span {
  margin-left: 14px;
  color: #7b9985;
}
.flow-illustration .illustration-primary {
  background: #366f50;
  color: white;
}
.story-footer {
  font-size: 12px;
  color: #697c70;
  display: flex;
  justify-content: space-between;
}
.auth-form {
  display: grid;
  place-items: center;
  padding: 40px;
}
.auth-card {
  width: min(100%, 370px);
}
.auth-card h2 {
  font-size: 30px;
  margin: 20px 0 12px;
}
.auth-card p {
  font-size: 14px;
  color: #89918d;
  margin-bottom: 32px;
}
.auth-submit {
  width: 100%;
  height: 44px;
  margin-top: 12px;
}
.auth-switch {
  text-align: center;
  font-size: 13px;
  margin-top: 24px;
}
.auth-note {
  border-top: 1px solid #eee;
  margin-top: 32px;
  padding-top: 24px;
  font-size: 12px;
  color: #969d99;
  text-align: center;
}
@media (max-width: 800px) {
  .auth-page {
    grid-template-columns: 1fr;
  }
  .auth-story {
    display: none;
  }
  .auth-form {
    min-height: 100vh;
  }
}
</style>
