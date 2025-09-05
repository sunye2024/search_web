<template>
  <div class="tabs-container">
    <div class="tab-scroll-wrapper">
      <div class="tabs">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ 'active': tab.key === currentTabKey }"
          @click="switchTab(tab.key)"
        >
          <span class="tab-title">{{ tab.title }}</span>
          <span
            class="tab-close"
            @click.stop="closeTab(tab.key)"
            v-if="tab.closable"
          >
            <i class="fa fa-times"></i>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

export default {
  name: 'Tabs',
  emits: ['tab-change'],
  setup(props, { emit }) {
    const route = useRoute();
    const router = useRouter();
    // 标签页数据
    const tabs = ref([
      {
        key: 'trace',
        title: '溯源',
        path: '/trace',
        closable: false
      }
    ]);
    // 当前激活的标签
    const currentTabKey = ref('trace');

    // 根据路由设置当前标签
    const setCurrentTabByRoute = () => {
      const routeName = route.name;
      let tabKey = 'trace';
      let tabTitle = '溯源';
      let path = '/trace';
      let closable = false;

      if (routeName === 'Search') {
        tabKey = 'trace';
        tabTitle = '溯源';
        path = route.fullPath;
      } else if (routeName === 'Path') {
        // 使用固定的key避免重复创建标签
        tabKey = 'path';
        tabTitle = `路径`;
        path = route.fullPath;
        closable = true;
      } else if (routeName === 'Event') {
        // 使用固定的key避免重复创建标签
        tabKey = 'event';
        tabTitle = '事件详情';
        path = route.fullPath;
        closable = true;
      }

      currentTabKey.value = tabKey;

      // 如果标签不存在，则添加
      if (!tabs.value.some(tab => tab.key === tabKey)) {
        tabs.value.push({
          key: tabKey,
          title: tabTitle,
          path,
          closable
        });
      } else {
        // 更新现有标签的路径
        const index = tabs.value.findIndex(t => t.key === tabKey);
        if (index !== -1) {
          tabs.value[index].path = path;
          if (routeName === 'Event') {
            tabs.value[index].title = tabTitle;
          }
        }
      }
    };

    // 初始设置
    setCurrentTabByRoute();

    // 监听路由变化
    watch(
      () => route.fullPath,
      () => {
        setCurrentTabByRoute();
      }
    );

    // 切换标签
    const switchTab = (key) => {
      const tab = tabs.value.find(t => t.key === key);
      if (tab) {
        currentTabKey.value = key;
        router.push(tab.path);
        emit('tab-change', tab);
      }
    };

    // 关闭标签
    const closeTab = (key) => {
      // 不能关闭最后一个标签
      if (tabs.value.length <= 1) {
        return;
      }

      const index = tabs.value.findIndex(t => t.key === key);
      if (index !== -1) {
        // 如果关闭的是当前标签，则切换到前一个标签
        if (key === currentTabKey.value) {
          const prevTab = tabs.value[index - 1] || tabs.value[0];
          switchTab(prevTab.key);
        }

        // 移除标签
        tabs.value.splice(index, 1);
      }
    };

    return {
      tabs,
      currentTabKey,
      switchTab,
      closeTab
    };
  }
};
</script>

<style scoped>
.tabs-container {
  height: 40px;
  background-color: #fff;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 20px;
  display: flex;
  align-items: center;
  overflow: hidden;
}

.tab-scroll-wrapper {
  flex: 1;
  overflow-x: auto;
  white-space: nowrap;
}

.tabs {
  display: inline-flex;
  height: 100%;
}

.tab-item {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 100%;
  cursor: pointer;
  position: relative;
  font-size: 14px;
  color: #595959;
}

.tab-item.active {
  color: #1890ff;
  border-bottom: 2px solid #1890ff;
}

.tab-item:hover {
  background-color: #f5f5f5;
}

.tab-title {
  margin-right: 8px;
}

.tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 12px;
  transition: all 0.3s;
}

.tab-close:hover {
  background-color: #f5f5f5;
  color: #f5222d;
}
</style>