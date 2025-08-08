<template>
  <div class="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
    <!-- 错误提示区域 -->
    <div v-if="errorMessage" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      {{ errorMessage }}
    </div>
    
    <!-- 溯源查询区域 -->
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h2 class="text-2xl font-bold text-gray-800 mb-4 flex items-center">
        <i class="fa fa-history text-primary mr-2"></i> 溯源查询
      </h2>
      
      <div class="flex flex-col md:flex-row gap-4 items-end">
        <div class="flex-1">
          <label for="queryContent" class="block text-sm font-medium text-gray-700 mb-1">查询内容</label>
          <div class="relative">
            <input 
              v-model="queryContent" 
              type="text" 
              id="queryContent" 
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-300"
              placeholder="请输入查询内容"
            >
            <div class="absolute right-3 top-2.5 text-gray-400">
              <i class="fa fa-search"></i>
            </div>
          </div>
        </div>
        
        <button 
          @click="executeSearch" 
          class="bg-primary hover:bg-primary/90 text-white font-medium py-2 px-6 rounded-lg transition-all duration-300 flex items-center shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
        >
          <i class="fa fa-search mr-2"></i> 查询
        </button>
      </div>
      
      <!-- 内容类型选择 -->
      <div class="mt-4 flex items-center gap-6 flex-wrap">
        <div v-for="type in contentTypes" :key="type.value" class="flex items-center">
          <input 
            type="radio" 
            :id="type.value + 'Type'" 
            v-model="contentType" 
            :value="type.value" 
            class="mr-2"
          >
          <label :for="type.value + 'Type'" class="text-gray-700">{{ type.label }}</label>
        </div>
        
        <div class="ml-auto">
          <label class="flex items-center px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <i class="fa fa-upload text-gray-500 mr-2"></i>
            <span class="text-sm text-gray-700">上传文件</span>
            <input type="file" class="hidden" @change="handleFileUpload">
          </label>
        </div>
      </div>
    </div>
    
    <!-- 结果展示区域 -->
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h3 class="text-xl font-semibold text-gray-800 mb-4">查询结果</h3>
      
      <!-- 加载状态 -->
      <div v-if="loadingTrace" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="mt-2 text-gray-500">正在查询数据...</p>
      </div>
      
      <!-- 结果表格 -->
      <div v-else>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">稿件(推文)</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">作者</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">发布时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">图片</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">视频</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">是否为源头</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(item, index) in results" :key="index" class="hover:bg-gray-50 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <a 
                    @click="loadGraphData(item.id)" 
                    class="text-primary hover:text-primary/80 hover:underline cursor-pointer font-medium"
                  >
                    {{ item.id }}
                  </a>
                </td>
                <td class="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">{{ item.content }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ item.author }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDate(item.publishTime) }}</td>
                <!-- 合并图片和视频显示逻辑 -->
                <td class="px-6 py-4 whitespace-nowrap text-sm" v-for="media in ['imageUrl', 'videoUrl']" :key="media">
                  <template v-if="item[media]">
                    <a :href="item[media]" target="_blank" class="text-primary hover:underline flex items-center">
                      <i :class="(media === 'imageUrl' ? 'fa fa-image' : 'fa fa-video-camera') + ' mr-1'"></i> 查看
                    </a>
                  </template>
                  <span v-else class="text-gray-400">Null</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span 
                    :class="item.isSource ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
                    class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                  >
                    {{ item.isSource ? '是' : '否' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- 图数据库展示区域 -->
    <div v-if="showGraph" class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h3 class="text-xl font-semibold text-gray-800 mb-4 flex items-center">
        <i class="fa fa-sitemap text-primary mr-2"></i> 关联图谱 (ID: {{ currentGraphId }})
        <button 
          @click="clearGraph" 
          class="ml-4 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <i class="fa fa-times mr-1"></i> 关闭图谱
        </button>
      </h3>
      
      <!-- 图谱加载状态 -->
      <div v-if="loadingGraph" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="mt-2 text-gray-500">正在加载关联图谱...</p>
      </div>
      
      <!-- 图谱内容 -->
      <div v-else>
        <div v-if="relatedData?.results?.length">
          <div ref="chartContainer" class="w-full h-[500px] border border-gray-200 rounded-lg mb-6"></div>
          
          <!-- 节点详情面板 -->
          <div v-if="selectedNode" class="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <div class="flex justify-between items-start">
              <h4 class="text-lg font-semibold text-gray-900">
                {{ nodeUtils.getTitle(selectedNode) }}
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
            
            <div v-if="selectedNode.publishtimestamp" class="text-sm text-gray-500 mt-1">
              {{ formatDate(selectedNode.publishtimestamp) }}
            </div>
            
            <div v-if="selectedNode.content" class="mt-4 text-gray-700">
              <p>{{ selectedNode.content }}</p>
            </div>
            
            <div class="mt-4 bg-gray-50 p-4 rounded-lg">
              <h5 class="font-medium text-gray-800 mb-2">节点属性</h5>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                <div><span class="font-medium">VID:</span> {{ selectedNode.vid || '-' }}</div>
                <div><span class="font-medium">类型:</span> {{ nodeUtils.getType(selectedNode) || '-' }}</div>
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
        
        <!-- 无数据提示 -->
        <div v-else class="text-center py-8 border border-dashed border-gray-200 rounded-lg">
          <i class="fa fa-search-minus text-gray-300 text-4xl mb-2"></i>
          <p class="text-gray-500">未找到与 "{{ currentGraphId }}" 相关的图谱数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, watch } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';

export default {
  name: 'TraceabilityWithGraph',
  setup() {
    // 溯源查询相关变量
    const queryContent = ref('');
    const contentType = ref('text');
    const contentTypes = [
      { value: 'text', label: '文本' },
      { value: 'image', label: '图片' },
      { value: 'video', label: '视频' }
    ];
    const loadingTrace = ref(false);
    const errorMessage = ref('');
    const results = ref([
      {
        id: 'e085dd440d864a08fad21c72edb26c7c',
        content: '测试文章1：这是一条关于食品安全的新闻报道，包含最新检测结果和专家解读',
        author: '食品安全播报',
        publishTime: 1625097600000,
        imageUrl: 'https://picsum.photos/200/300?random=1',
        videoUrl: '',
        isSource: true
      },
      {
        id: '734112c5ce82e42b40a8bf6888ffc1f5',
        content: '过年回家的意义在此刻具象化了',
        author: '健康养生达人',
        publishTime: 1625184000000,
        imageUrl: '',
        videoUrl: 'https://example.com/videos/food-safety.mp4',
        isSource: false
      },
      {
        id: '6bf3f206e91d27df51c29ca5a396bcc1',
        content: '专家解读：如何辨别食品标签真伪，避免购买不合格产品',
        author: '营养专家李教授',
        publishTime: 1625270400000,
        imageUrl: 'https://picsum.photos/200/300?random=2',
        videoUrl: 'https://example.com/videos/food-label.mp4',
        isSource: true
      }
    ]);
    const searchExecuted = ref(true);
    const selectedFile = ref(null);
    
    // 图谱相关变量
    const currentGraphId = ref('');
    const showGraph = ref(false);
    const relatedData = ref(null);
    const loadingGraph = ref(false);
    const chart = ref(null);
    const selectedNode = ref(null);
    const chartContainer = ref(null);
    const isDataReady = ref(false);
    const isContainerReady = ref(false);
    
    // 节点工具函数整合
    const nodeUtils = {
      getDisplayName: (item) => {
        if (item.title) return item.title;
        if (item.eventstr) return item.eventstr;
        if (item.name) return item.name;
        return item.vid || '未知节点';
      },
      getType: (item) => {
        if (item.eventstr) return '事件 (Event)';
        if (item.title || item.content) return '文章 (Article)';
        if (item.forwardcount !== undefined) return '原始推文 (Original_Tweet)';
        if (item.retext) return '转发推文 (Retweet)';
        return '未知类型 (Unknown)';
      },
      getBaseType: (item) => {
        if (item.eventstr) return 'Event';
        if (item.title || item.content) return 'Article';
        if (item.forwardcount !== undefined) return 'Original_Tweet';
        if (item.retext) return 'Retweet';
        return 'Unknown';
      },
      getSize: (type) => ({
        'Event': 60,
        'Article': 40,
        'Original_Tweet': 30,
        'Retweet': 25,
        'Unknown': 35
      }[type] || 30),
      getColor: (type, item) => {
        if (type === 'Article') return item.isrumor ? '#EA4335' : '#34A853';
        return {
          'Event': '#4285F4',
          'Original_Tweet': '#FBBC05',
          'Retweet': '#F29900',
          'Unknown': '#90A4AE'
        }[type] || '#90A4AE';
      },
      getTitle: (node) => {
        if (node.title) return node.title;
        if (node.eventstr) return node.eventstr;
        if (node.name) return node.name;
        return '节点详情';
      }
    };
    
    // 加载图谱数据
    const loadGraphData = async (id) => {
      currentGraphId.value = id;
      showGraph.value = true;
      loadingGraph.value = true;
      
      try {
        const response = await axios.get('http://localhost:5000/api/getRelatedByEventVid', {
          params: { event_vid: id }
        });
        
        relatedData.value = null;
        await nextTick();
        relatedData.value = response.data;
        
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
    
    // 清除图谱显示
    const clearGraph = () => {
      showGraph.value = false;
      currentGraphId.value = '';
      relatedData.value = null;
      selectedNode.value = null;
      if (chart.value) {
        chart.value.dispose();
        chart.value = null;
      }
    };
    
    // 溯源查询方法
    const executeSearch = async () => {
      if (!queryContent.value.trim() && !selectedFile.value) {
        errorMessage.value = "请输入查询内容或上传文件";
        return;
      }

      loadingTrace.value = true;
      searchExecuted.value = true;
      errorMessage.value = '';
      
      try {
        const response = await axios.post('http://localhost:5000/api/traceability/search', {
          content: queryContent.value,
          type: contentType.value,
          hasFile: !!selectedFile.value
        });
        results.value = response.data.results;
      } catch (error) {
        console.error('查询失败:', error);
        errorMessage.value = error.response?.data?.error || '查询过程中发生错误，请重试';
      } finally {
        loadingTrace.value = false;
      }
    };

    const handleFileUpload = (e) => {
      if (e.target.files?.[0]) {
        selectedFile.value = e.target.files[0];
        errorMessage.value = '';
      }
    };
    
    // 图谱绘制相关
    watch(chartContainer, (newValue) => {
      if (newValue) {
        isContainerReady.value = true;
        tryDrawGraph();
      }
    });
    
    watch(relatedData, () => {
      if (relatedData.value?.results?.length) {
        isDataReady.value = true;
        tryDrawGraph();
      }
    });
    
    const tryDrawGraph = () => {
      if (isDataReady.value && isContainerReady.value && showGraph.value) {
        drawGraph();
      }
    };
    
    // 错误处理
    const handleError = (error) => {
      if (error.response) {
        errorMessage.value = `请求失败 (${error.response.status}): ${error.response.data.error || '未知错误'}`;
      } else if (error.request) {
        errorMessage.value = "没有收到服务器响应";
      } else {
        errorMessage.value = `请求错误: ${error.message}`;
      }
    };
    
    // 绘制关系图
    const drawGraph = () => {
      if (!chartContainer.value || !relatedData.value?.results || !currentGraphId.value) return;
      
      if (chart.value) chart.value.dispose();
      chart.value = echarts.init(chartContainer.value);
      
      // 准备数据
      const nodes = new Map();
      const links = [];
      const nodeTypes = new Map();
      
      // 添加中心事件节点
      nodes.set(currentGraphId.value, {
        name: currentGraphId.value,
        symbolSize: 60,
        itemStyle: { color: '#4285F4' },
        category: 0,
        draggable: true,
        originalData: { vid: currentGraphId.value, type: 'Event' }
      });
      nodeTypes.set('Event', 0);
      
      // 处理结果数据
      relatedData.value.results.forEach((item) => {
        if (!nodes.has(item.vid)) {
          const nodeType = nodeUtils.getBaseType(item);
          let category = nodeTypes.get(nodeType);
          if (category === undefined) {
            category = nodeTypes.size;
            nodeTypes.set(nodeType, category);
          }
          
          nodes.set(item.vid, {
            name: nodeUtils.getDisplayName(item),
            symbolSize: nodeUtils.getSize(nodeType),
            itemStyle: { color: nodeUtils.getColor(nodeType, item) },
            category: category,
            draggable: true,
            originalData: item
          });
        }
        
        if (item.end_vid && nodes.has(item.end_vid)) {
          links.push({
            source: item.vid,
            target: item.end_vid,
            lineStyle: { color: '#90A4AE', width: 1.5 },
            label: { show: !!item.e_type, formatter: item.e_type || '' }
          });
        }
      });
      
      // 配置项
      const option = {
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          borderColor: '#eee',
          borderWidth: 1,
          padding: 10,
          textStyle: { color: '#333' },
          formatter: (params) => {
            if (params.data?.originalData) {
              const data = params.data.originalData;
              return `
                <div class="p-3 bg-white rounded-lg shadow-lg border border-gray-200">
                  <h3 class="font-bold text-gray-900 mb-1">${nodeUtils.getDisplayName(data)}</h3>
                  <div class="text-xs text-gray-500 mb-2">
                    <span>${nodeUtils.getBaseType(data)}</span>
                    ${data.publishtimestamp ? `<span class="mx-1">•</span><span>${formatDate(data.publishtimestamp)}</span>` : ''}
                  </div>
                  ${data.isrumor !== undefined ? `
                    <div class="text-sm text-gray-700">
                      <span class="font-medium">状态:</span> 
                      <span class="${data.isrumor ? 'text-red-600' : 'text-green-600'} font-medium">
                        ${data.isrumor ? '谣言' : '真实'}
                      </span>
                    </div>
                  ` : ''}
                </div>
              `;
            }
            return params.name;
          }
        },
        legend: [{
          data: Array.from(nodeTypes.entries()).map(([name]) => name),
          orient: 'horizontal',
          left: 'center',
          top: 'bottom'
        }],
        series: [{
          type: 'graph',
          layout: 'force',
          data: Array.from(nodes.values()),
          links: links,
          categories: Array.from(nodeTypes.entries()).map(([name]) => ({ name })),
          roam: true,
          focusNodeAdjacency: true,
          force: {
            repulsion: 500,
            edgeLength: [50, 150],
            gravity: 0.2,
            layoutAnimation: true,
            animationDuration: 300,
            animationEasing: 'cubicOut'
          },
          label: {
            show: true,
            position: 'top',
            formatter: (params) => params.name.length > 8 ? params.name.substring(0, 8) + '...' : params.name
          },
          emphasis: { label: { show: true, fontSize: 16 } },
          lineStyle: { color: 'source', curveness: 0.1 }
        }]
      };
      
      chart.value.setOption(option);
      chart.value.on('click', (params) => {
        if (params.data?.originalData) selectedNode.value = params.data.originalData;
      });
    };
    
    // 关闭节点详情
    const closeNodeDetail = () => { selectedNode.value = null; };
    
    // 日期格式化
    const formatDate = (timestamp) => {
      return timestamp ? new Date(timestamp).toLocaleString() : '';
    };
    
    onMounted(() => {
      window.addEventListener('resize', () => {
        chart.value?.resize();
      });
    });
    
    return {
      // 溯源查询相关
      queryContent,
      contentType,
      contentTypes,
      loadingTrace,
      errorMessage,
      results,
      searchExecuted,
      executeSearch,
      handleFileUpload,
      
      // 图谱相关
      currentGraphId,
      showGraph,
      relatedData,
      loadingGraph,
      selectedNode,
      chartContainer,
      loadGraphData,
      clearGraph,
      closeNodeDetail,
      nodeUtils,
      
      // 通用方法
      formatDate
    };
  }
};
</script>

<style scoped>
.container {
  max-width: 1400px;
  padding-top: 2rem;
}

@media (min-width: 1200px) {
  .container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

/* 表格样式优化 */
table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
}

th, td {
  border-bottom: 1px solid #e5e7eb;
}

th:first-child { border-radius: 0.5rem 0 0 0; }
th:last-child { border-radius: 0 0.5rem 0 0; }
tr:last-child td { border-bottom: none; }

/* 自定义样式 */
.break-url { word-break: break-all; }
</style>