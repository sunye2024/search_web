<template>
  <div class="path-view">
    <div class="bg-white rounded-white rounded rounded-xl shadow-lg p-6 mb-6">
      <h3 class="text-xl font-semibold text-gray-800 mb-4 flex items-center"> 传播图谱
        <!-- 只在有加载结果时显示查询标题和关闭按钮 -->
        <span v-if="hasSearched && currentGraphEvent" class="ml-2 text-sm text-gray-500">查询:事件_ {{ currentGraphEvent }}</span>
        <button 
          @click="clearGraph" 
          class="ml-4 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          v-if="hasSearched && currentGraphEvent"
        >
          <i class="fa fa-times mr-1"></i> 关闭图谱
        </button>
      </h3>
      
      <!-- 图谱EVENT输入 -->
      <div class="mb-4 flex items-center">
        <label for="graphEvent" class="block text-sm font-medium text-gray-700 mr-2">查询内容:</label>                  
        <input 
          v-model="currentGraphEvent" 
          type="text" 
          id="graphEvent" 
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-300"
          placeholder="请输入事件名称查看传播图谱"
        >
        <button 
          @click="loadGraphData(currentGraphEvent)" 
          class="ml-2 bg-primary hover:bg-primary/90 text-white font-medium py-2 px-4 rounded-lg transition-all duration-300"
          :disabled="!currentGraphEvent"
        >
          加载
        </button>
      </div>
      
      <!-- 图谱加载状态 -->
      <div v-if="loadingGraph" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="mt-2 text-gray-500">正在加载传播图谱...</p>
      </div>
      
      <!-- 图谱内容 -->
      <div v-else>
        <!-- 只有执行过搜索后才显示结果区域 -->
        <template v-if="hasSearched">
          <!-- 有数据时显示图 -->
          <div v-if="relatedData && relatedData.results && relatedData.results.length > 0">
            <div ref="chartContainer" class="w-full h-[500px] border border-gray-200 rounded-lg mb-6"></div>
            
            <!-- 节点详情面板 -->
            <div v-if="selectedNode" class="bg-white rounded-xl shadow-md p-6 border border-gray-100">
              <div class="flex justify-between items-start">
                <h4 class="text-lg font-semibold text-gray-900">
                  {{ getNodeTitle(selectedNode) }}
                </h4>
                <span 
                  v-if="selectedNode.isrumor !== null" 
                  :class="{
                    'bg-green-100 text-green-800': !selectedNode.isrumor,
                    'bg-red-100 text-red-800': selectedNode.isrumor
                  }" 
                  class="text-xs px-2 py-0.5 rounded font-medium"
                >
                  {{ selectedNode.isrumor ? '谣言' : '真实' }}
                </span>
              </div>
              <div v-if="(selectedNode.publishtimestamp || selectedNode.republishtime) || selectedNode.datasource" class="text-sm text-gray-500 mt-1">
<span v-if="selectedNode.publishtimestamp || selectedNode.republishtime">
  {{ formatDate(selectedNode.publishtimestamp || selectedNode.republishtime) }}
</span>
<span v-if="selectedNode.datasource" class="ml-3">
  数据源：{{ selectedNode.datasource }}
</span>
</div>

              <div v-if="selectedNode.content" class="mt-4 text-gray-700">
                <p>{{ selectedNode.content }}</p>
              </div>
              
              <div class="mt-4 bg-gray-50 p-4 rounded-lg">
                <h5 class="font-medium text-gray-800 mb-2">节点属性</h5>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div><span class="font-medium">VID:</span> {{ selectedNode.vid || '-' }}</div>
                  <div><span class="font-medium">类型:</span> {{ getNodeType(selectedNode) || '-' }}</div>
                  <template v-for="(value, key) in selectedNode" :key="key">
                    <div v-if="!['vid', 'e_type', 'title', 'content', 'publishtimestamp', 'isrumor'].includes(key)">
                      <span class="font-medium">{{ key }}:</span> {{ value || '-' }}
                    </div>
                  </template>
                </div>
              </div>
              
              <button 
                @click="closeNodeDetail" 
                class="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors duration-200"
              >
                <i class="fa fa-times mr-1"></i> 关闭详情
              </button>
            </div>
          </div>
          
          <!-- 无数据时显示提示 -->
          <div v-else class="text-center py-8 border border-dashed border-gray-200 rounded-lg">
            <i class="fa fa-search-minus text-gray-300 text-4xl mb-2"></i>
            <p class="text-gray-500">未找到与 "{{ currentGraphEvent }}" 相关的图谱数据</p>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { getGraphDataByEvent } from '../../service/apiManager.js';
import { formatDate } from '../../utils/date.js';
import { useRouter } from 'vue-router'; // 顶部添加导入
export default {
  name: 'EventView',
  props: {
    initialGraphEvent: {
      type: String,
      default: ''
    }
  },
  emits: ['clearGraph'],
  setup(props, { emit }) {
    // 图谱相关变量
    const currentGraphEvent = ref(props.initialGraphEvent);
    const relatedData = ref(null);
    const loadingGraph = ref(false);
    const chart = ref(null);
    const selectedNode = ref(null);
    const chartContainer = ref(null);
    const isDataReady = ref(false);
    const isContainerReady = ref(false);
    const errorMessage = ref('');
    // 新增：标记是否执行过搜索
    const hasSearched = ref(!!props.initialGraphEvent);
    const router = useRouter();
    
    // 时间格式化
    const formatDate = (timestamp) => {
      if (!timestamp) return '';
      // 处理秒级时间戳（转换为毫秒）
      let msTimestamp = timestamp;
      if (String(timestamp).length < 13) {
        msTimestamp = Number(timestamp) * 1000;
      }
      const date = new Date(msTimestamp);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
    };
    
    // 加载图谱数据
    const loadGraphData = async (Event) => {
      if (!Event) return;
      
      loadingGraph.value = true;
      errorMessage.value = '';
      // 标记为已执行搜索
      hasSearched.value = true;
      try {
        const response = await getGraphDataByEvent(Event);
        
        // 清空旧数据
        relatedData.value = null;
        await nextTick();
        
        // 更新数据
        relatedData.value = response.data;
        
        // 强制重绘
        isDataReady.value = false;
        nextTick(() => {
          isDataReady.value = true;
          tryDrawGraph();
        });
      } catch (error) {
        console.error('查询关联内容失败:', error);
        handleError(error);
      } finally {
        loadingGraph.value = false;
      }
    };
    // 监听路由参数变化
    watch(
      () => router.currentRoute.value.query.event,
      (newEvent) => {
        if (newEvent && newEvent !== currentGraphEvent.value) {
          console.log('从路由参数接收事件名称:', newEvent);
          currentGraphEvent.value = newEvent;
          loadGraphData(newEvent); // 自动加载数据
        }
      },
      { immediate: true } // 初始化时立即执行
    );

    // 监听初始图谱事件变化
    watch(() => props.initialGraphEvent, (newEvent) => {
      console.log('EventView: initialGraphEvent changed to:', newEvent);
      currentGraphEvent.value = newEvent;
      if (newEvent) {
        loadGraphData(newEvent);
      }
    });
    // 清除图谱显示
    const clearGraph = () => {
      currentGraphEvent.value = '';
      relatedData.value = null;
      selectedNode.value = null;
      // 重置搜索状态
      hasSearched.value = false;
      
      // 销毁图表实例
      if (chart.value) {
        chart.value.dispose();
        chart.value = null;
      }
      
      // 通知父组件清除图谱
      emit('clearGraph');
    };
    
    // 图谱相关方法
    watch(chartContainer, (newValue) => {
      if (newValue) {
        isContainerReady.value = true;
        tryDrawGraph();
      }
    });
    
    watch(relatedData, () => {
      if (relatedData.value && relatedData.value.results && relatedData.value.results.length > 0) {
        isDataReady.value = true;
        tryDrawGraph();
      }
    });
    
    const tryDrawGraph = () => {
      if (isDataReady.value && isContainerReady.value) {
        drawGraph();
      }
    };
    
    // 错误处理
    const handleError = (error) => {
      if (error.response) {
        console.error(`请求失败 (${error.response.status}):`, error.response.data);
      } else if (error.request) {
        console.error("没有收到服务器响应:", error.request);
      } else {
        console.error("请求错误:", error.message);
      }
    };
    
    // 绘制关系图
    const drawGraph = () => {
      if (!chartContainer.value || !relatedData.value?.results || !currentGraphEvent.value) {
        console.error('Chart container or data not found');
        return;
      }
      
      // 销毁旧的图表实例
      if (chart.value) {
        chart.value.dispose();
      }
      
      // 初始化图表
      chart.value = echarts.init(chartContainer.value);
      
      // 准备数据
      const nodes = new Map();
      const links = [];
      const nodeTypes = new Map();
      let nextCategoryId = 0;
      
    // 中心事件节点ID
    const centerEventId = currentGraphEvent.value;
    
    // 添加中心事件节点（唯一Event类型节点）
    nodes.set(centerEventId, {
      id: centerEventId,
      name: centerEventId,
      symbolSize: 60,
      itemStyle: { color: '#1890ff' },
      category: 0,
      draggable: true,
      originalData: { vid: centerEventId, type: 'Event' }
    });
    nodeTypes.set('Event', 0);
    nextCategoryId = 1;
    
    // 处理结果数据，提取节点和边
    relatedData.value.results.forEach((item) => {
      // 必须存在源节点ID才处理
      if (!item.e_src) {
        console.warn('跳过无效边数据:', item);
        return;
      }

      // 获取节点类型和属性
      const srcNodeType = item.src_type || 'Unknown';
      const srcNodeProps = item.src_props || {};

      // 初始化源和目标节点
      let source = item.e_src;
      let target;
      
      // 处理belong边：强制目标为中心事件节点
      if (item.e_type === 'belong') {
        target = centerEventId;
      } 
      // 处理forwarded边：使用原始目标
      else if (item.e_type === 'forwarded') {
        if (!item.e_dst) return; // 过滤无效目标
        target = item.e_dst;
      }
      // 过滤其他类型边
      else {
        return;
      }

      // 添加源节点（确保非Event类型）
      if (!nodes.has(source)) {
        // 排除源节点为Event类型（确保唯一）
        const finalSrcType = srcNodeType === 'Event' ? 'Unknown' : srcNodeType;

        if (!nodeTypes.has(finalSrcType)) {
          nodeTypes.set(finalSrcType, nextCategoryId);
          nextCategoryId++;
        }
        
        // 处理节点名称
        let nodeName = srcNodeProps.title;
        if (!nodeName && srcNodeProps.content) {
          nodeName = srcNodeProps.content.substring(0, 8) + '...';
        } else if (!nodeName && srcNodeProps.retext) {
          nodeName = srcNodeProps.retext.substring(0, 8) + '...';
        } else {
          nodeName = srcNodeProps.title.substring(0, 8) + '...';
        }
        
        nodes.set(source, {
          id: source,
          name: nodeName,
          symbolSize: getNodeSizeByType(finalSrcType),
          itemStyle: { color: getNodeColorByType(finalSrcType) },
          category: nodeTypes.get(finalSrcType),
          draggable: true,
          originalData: { ...srcNodeProps, vid: source, type: finalSrcType }
        });
      }

      // 为forwarded边添加目标节点（排除Event类型）
      if (item.e_type === 'forwarded' && !nodes.has(target)) {
        const dstNodeType = item.dst_type || 'Unknown';
        const dstNodeProps = item.dst_props || {};
        
        // 排除目标节点为Event类型
        const finalDstType = dstNodeType === 'Event' ? 'Unknown' : dstNodeType;

        if (!nodeTypes.has(finalDstType)) {
          nodeTypes.set(finalDstType, nextCategoryId);
          nextCategoryId++;
        }
        
        let nodeName = dstNodeProps.title || dstNodeProps.name;
        if (!nodeName) {
          nodeName = target.slice(0, 8) + '...';
        }
        
        nodes.set(target, {
          id: target,
          name: nodeName,
          symbolSize: getNodeSizeByType(finalDstType),
          itemStyle: { color: getNodeColorByType(finalDstType) },
          category: nodeTypes.get(finalDstType),
          draggable: true,
          originalData: { ...dstNodeProps, vid: target, type: finalDstType }
        });
      }

      // 添加边
      links.push({
        source: source,
        target: target,
        name: item.e_type,
        lineStyle: {
          width: item.e_type === 'belong' ? 3 : 2,
          curveness: item.e_type === 'belong' ? 0.1 : 0.2,
          color: item.e_type === 'belong' ? '#52c41a' : '#faad14',
          opacity: 0.9
        }
      });
    });
    
    // 图表配置
    const option = {
      tooltip: {
        formatter: function(params) {
          if (params.dataType === 'node') {
            return `${params.data.name}<br/>类型: ${params.data.originalData.type}`;
          } else if (params.dataType === 'edge') {
            return `关系: ${params.data.name}`;
          }
          return params.name;
        }
      },
      legend: {
        data: Array.from(nodeTypes.entries())
          .filter(([type]) => type)
          .map(([type]) => type),
        bottom: 10
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          force: {
            repulsion: 350,
            edgeLength: 120
          },
          roam: true,
          label: {
            show: true,
            fontSize: 12,
            overflow: 'truncate'
          },
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [0, 8],
          edgeLabel: {
            fontSize: 10,
            formatter: '{b}'
          },
          data: Array.from(nodes.values()),
          links: links,
          categories: Array.from(nodeTypes.entries()).map(([type]) => ({ 
            name: type,
            itemStyle: { color: getNodeColorByType(type) }
          }))
        }
      ]
    };
    
    chart.value.setOption(option);
    
    // 节点点击事件
    chart.value.on('click', (params) => {
      if (params.dataType === 'node') {
        if (params.data.originalData?.type === 'Event') {
              window.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
              selectedNode.value = params.data.originalData;
            }
      }
    });
    
    // 窗口大小变化时重绘图表
    window.addEventListener('resize', () => {
      if (chart.value) {
        chart.value.resize();
      }
    });
  };

  // 辅助函数：根据节点类型获取颜色
  const getNodeColorByType = (type) => {
    const colorMap = {
      'Event': '#1890ff',       // 事件节点用蓝色
      'Article': '#34A853',     // 文章用绿色
      'Original_Tweet': '#FBBC05', // 原始推文用黄色
      'Retweet': '#F2994A',     // 转发用橙色
      'User': '#9B51E0',        // 用户用紫色
      'Comment': '#EA4335',     // 评论用红色
      'Unknown': '#8884d8'      // 未知类型
    };
    return colorMap[type] || colorMap['Unknown'];
  };
  
  // 辅助函数：根据节点类型获取大小
  const getNodeSizeByType = (type) => {
    const sizeMap = {
      'Event': 50,
      'Article': 40,
      'Original_Tweet': 40,
      'Retweet': 35,
      'User': 30,
      'Comment': 30,
      'Unknown': 35
    };
    return sizeMap[type] || sizeMap['Unknown'];
  };

  // 关闭节点详情
  const closeNodeDetail = () => {
    selectedNode.value = null;
  };
  
  // 获取节点标题
  const getNodeTitle = (node) => {
      // 检查节点类型属性并返回对应标题
if (node.type === 'Retweet') {
  return '转发节点';
} else if (node.type === 'Original_Tweet') {
  return '微博文章';
}
// 其余保持
return node.title;
  };
  
  // 获取节点类型
  const getNodeType = (node) => {
    return node.type || node.e_type || '未知类型';
  };
  
  return {
    currentGraphEvent,
    relatedData,
    loadingGraph,
    chart,
    selectedNode,
    chartContainer,
    errorMessage,
    hasSearched, // 导出新状态变量
    loadGraphData,
    clearGraph,
    closeNodeDetail,
    getNodeTitle,
    getNodeType,
    formatDate
  };
}
};
</script>

<style scoped>
/* 原内容样式适配 */
.path-view {
  width: 100%;
}

/* 确保表格在侧边栏切换时能正确适应宽度 */
.overflow-x-auto {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

/* 按钮和交互元素样式统一 */
button {
  cursor: pointer;
}

/* 动画效果 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 定义主题色变量 */
:root {
  --primary-color: #1890ff;
}

.text-primary {
  color: #1890ff !important;
}

.border-primary {
  border-color: #1890ff !important;
}

.bg-primary {
  background-color: #1890ff !important;
}

.focus\:ring-primary\/50:focus {
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.5) !important;
}

.focus:border-primary:focus {
  border-color: #1890ff !important;
}
</style>