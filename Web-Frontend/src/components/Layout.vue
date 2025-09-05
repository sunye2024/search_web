<template>
  <div class="traceability-container">
    
    <!-- 错误提示区域 -->
    <div v-if="errorMessage" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      {{ errorMessage }}
    </div>
    
    <!-- 溯源查询和结果区域 -->
    <keep-alive>
      <SearchView 
        v-if="activeTab === 'trace'" 
        :key="$route.fullPath"
        @switch-to-path-with-id="handleSwitchToPathWithId"
      />
    </keep-alive>
    
    <!-- 路径（关联图谱）区域 -->
    <PathView 
      v-if="activeTab === 'tool-path'"
      :initial-graph-id="currentGraphId"
      :initial-event="currentGraphEvent"
      @clear-graph="handleClearGraph"
    />
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import SearchView from '../views/trace/SearchView.vue';
import PathView from '../views/trace/PathView.vue';

export default {
  props: {
    activeTab: {
      type: String,
      required: true
    }
  },
  name: 'TraceabilitySystem',
  components: {
    SearchView,
    PathView
  },
  setup() {
    // 导航标签 - 控制当前显示哪个标签页
    // 从父组件接收activeTab作为prop

    const errorMessage = ref('');
    // 当前图谱ID
    const currentGraphId = ref('');
    
    // 处理切换到路径标签并通过ID加载图谱
    const router = useRouter();
    const handleSwitchToPathWithId = (params) => {
      // 仅验证ID，event可选
      if (!params?.id) {
        errorMessage.value = "ID不存在";
        return;
      }
      console.log('尝试跳转，ID:', params.id, 'Event:', params.event);
      // 切换到路径标签页
      // 通知父组件切换标签
      emit('update:activeTab', 'tool-path');
      router.push({ name: 'Path' });
      // 设置当前图谱ID和事件名
      currentGraphId.value = params.id;
      // 即使event不存在也继续传递
      currentGraphEvent.value = params.event || '';
    };
    
    // 处理清除图谱
    const handleClearGraph = () => {
      currentGraphId.value = '';
      activeTab.value = 'trace';
    };
    
    return {
        activeTab: props.activeTab,
      // activeTab由父组件控制
      errorMessage,
      currentGraphId,
      currentGraphEvent,
      handleSwitchToPathWithId,
      handleClearGraph
    };
  }
};
</script>

<style scoped>
.traceability-container {
  width: 100%;
}

/* 导航栏样式 */
nav {
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

nav .flex {
  display: flex;
  gap: 2rem;
}

button {
  padding: 1rem 0.25rem;
  border-bottom: 2px solid transparent;
  font-weight: 500;
  font-size: 0.875rem;
  transition: color 0.2s, border-color 0.2s;
}

button.border-primary {
  color: #1890ff;
  border-color: #1890ff;
}

button:not(.border-primary) {
  color: #6b7280;
}

button:not(.border-primary):hover {
  color: #374151;
  border-color: #d1d5db;
}

/* 错误提示区域样式 */
.bg-red-100 {
  background-color: #fee2e2;
}

.border-red-400 {
  border-color: #f87171;
}

.text-red-700 {
  color: #b91c1c;
}

.px-4 {
  padding-left: 1rem;
  padding-right: 1rem;
}

.py-3 {
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.rounded {
  border-radius: 0.25rem;
}

.mb-4 {
  margin-bottom: 1rem;
}
</style>