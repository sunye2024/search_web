<template>
  <header class="app-header">
    <div class="header-left">
      <button 
        class="sidebar-toggle" 
        @click="toggleSidebar"
      >
        <i class="fa" :class="sidebarOpened ? 'fa-angle-left' : 'fa-angle-right'"></i>
      </button>
      <div class="logo">
        <img src="/logo.png" alt="Logo">
        <span>演示系统</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-info">
        <img src="/user-avatar.png" alt="用户头像" class="avatar">
        <span>管理员</span>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'Header',
  props: {
    sidebarOpened: {
      type: Boolean,
      default: true
    }
  },
  emits: ['toggleSidebar'],
  setup(props, { emit }) {
    const toggleSidebar = () => {
      emit('toggleSidebar');
    };
    
    return {
      toggleSidebar
    };
  }
};
</script>

<style scoped>
/* 顶部导航栏 */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 20px;
  background-color: #1890ff;
  color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
}

.sidebar-toggle {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 18px;
  margin-right: 15px;
  cursor: pointer;
}

.logo {
  display: flex;
  align-items: center;
}

.logo img {
  height: 30px;
  margin-right: 10px;
  vertical-align: middle;
}

.logo span {
  font-size: 18px;
  font-weight: bold;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  margin-right: 10px;
  border: 2px solid rgba(255, 255, 255, 0.5);
}
</style>