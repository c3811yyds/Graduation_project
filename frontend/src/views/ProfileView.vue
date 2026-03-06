<template>
  <div class="page profile-page-wrapper">
    <div class="panel profile-panel">
      <!-- 顶部头像与标题区域 -->
      <div class="profile-header">
        <div class="avatar-placeholder">
          {{ form.username ? form.username.charAt(0).toUpperCase() : 'U' }}
        </div>
        <div class="profile-title">
          <h2>个人中心</h2>
          <p class="muted">管理并完善您的账号资料</p>
        </div>
      </div>

      <div class="profile-form">
        <div class="form-group row-group">
          <label>用户名</label>
          <div class="input-wrapper">
            <input class="form-control" v-model="form.username" placeholder="请输入个性化用户名" />
            <span class="hint" style="margin-top: 6px; display: block; font-size: 12px; color: #94a3b8;">* 将作为账号和社区显示名</span>
          </div>
        </div>

        <div class="form-group row-group">
          <label>性别</label>
          <div class="radio-group">
            <label class="radio-label" :class="{ active: form.gender === '男' }">
              <input type="radio" value="男" v-model="form.gender" />
              <span>男</span>
            </label>
            <label class="radio-label" :class="{ active: form.gender === '女' }">
              <input type="radio" value="女" v-model="form.gender" />
              <span>女</span>
            </label>
            <label class="radio-label" :class="{ active: form.gender === '未知' }">
              <input type="radio" value="未知" v-model="form.gender" />
              <span>保密</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>爱好与个人简介</label>
          <textarea class="form-control custom-textarea" v-model="form.hobby" rows="5" placeholder="向大家简单介绍一下您的爱好或近期学习目标..."></textarea>
        </div>

        <div class="action-group">
          <button class="btn btn-primary save-btn" @click="saveProfile">
            保存修改
          </button>
          <button class="btn return-btn" @click="$router.push('/')">
            返回首页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import http from '../api/http';

const router = useRouter();
const form = ref({
  username: '',
  gender: '未知',
  hobby: ''
});

onMounted(async () => {
  try {
    // [后端映射]: GET /api/users/me -> 读取个人资料
    const res = await http.get('/users/me');
    const u = res.data.data;
    form.value.username = u.username || '';
    form.value.gender = u.gender || '未知';
    form.value.hobby = u.hobby || '';
  } catch (err) {
    if (err.response?.status === 401) {
      router.push('/');
    }
  }
});

async function saveProfile() {
  if (!form.value.username.trim()) {
    alert("用户名不能为空");
    return;
  }
  try {
    // [后端映射]: PATCH /api/users/me -> 更新个人资料
    await http.patch('/users/me', form.value);
    alert("个人资料更新成功！");
    // 更新完成后重新加载页面使状态生效
    window.location.reload();
  } catch (e) {
    alert(e?.response?.data?.message || "更新失败，请重试");
  }
}
</script>

<style scoped>
.profile-page-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 40px;
}

.profile-panel {
  max-width: 600px;
  width: 100%;
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
  background: white;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 40px;
  padding-bottom: 30px;
  border-bottom: 1px solid #f1f5f9;
}

.avatar-placeholder {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  font-size: 32px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
}

.profile-title h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #1e293b;
}

.profile-title p {
  margin: 0;
  font-size: 14px;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group label {
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: center;
  font-size: 15px;
}

.form-control {
  padding: 12px 16px;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 15px;
  transition: all 0.2s ease;
  width: 100%;
  box-sizing: border-box;
  background-color: #f8fafc;
}

.form-control:focus {
  border-color: #3b82f6;
  background-color: #fff;
  outline: none;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.custom-textarea {
  resize: vertical;
  line-height: 1.6;
}

/* Radio Group Styles */
.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 24px;
  border: 1.5px solid #e2e8f0;
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: #f8fafc;
  color: #64748b;
  font-weight: 500;
}

.radio-label input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
}

.radio-label:hover {
  border-color: #cbd5e1;
  background-color: #f1f5f9;
}

.radio-label.active {
  border-color: #3b82f6;
  background-color: #eff6ff;
  color: #1d4ed8;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.action-group {
  margin-top: 20px;
  display: flex;
  gap: 16px;
  align-items: center;
  border-top: 1px solid #f1f5f9;
  padding-top: 30px;
}

.save-btn {
  padding: 12px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
  transition: all 0.2s;
}

.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.3);
}

.return-btn {
  padding: 12px 24px;
  background-color: white;
  border: 1.5px solid #e2e8f0;
  color: #64748b;
  border-radius: 10px;
  font-weight: 500;
}

.return-btn:hover {
  background-color: #f8fafc;
  color: #475569;
}
</style>
