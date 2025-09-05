<template>
  <div class="path-view">
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h3 class="text-xl font-semibold text-gray-800 mb-4 flex items-center"> 传播图谱
        <!-- 修改：只有加载过数据后才显示查询信息 -->
        <span v-if="hasSearched && currentGraphId" class="ml-2 text-sm text-gray-500">查询:推文_ {{ currentGraphId }}</span>
        <button 
          @click="clearGraph" 
          class="ml-4 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          v-if="hasSearched && currentGraphId"
        >
          <i class="fa fa-times mr-1"></i> 关闭图谱
        </button>
      </h3>
      
      <!-- 图谱ID输入 -->
      <div class="mb-4 flex items-center">
        <label for="graphId" class="block text-sm font-medium text-gray-700 mr-2">查询内容:</label>                  
        <input 
          v-model="currentGraphId" 
          type="text" 
          id="graphId" 
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-300"
          placeholder="请输入推文ID查看传播图谱"
        >
        <button 
          @click="loadGraphData(currentGraphId)" 
          class="ml-2 bg-primary hover:bg-primary/90 text-white font-medium py-2 px-4 rounded-lg transition-all duration-300"
          :disabled="!currentGraphId"
        >
          加载
        </button>
      </div>
      

      <!-- 新增推文原文板块 -->
      <div v-if="hasSearched && originalTweet && originalTweet.results && originalTweet.results.length > 0" class="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h4 class="text-lg font-semibold text-gray-800 mb-3">推文原文</h4>
      <div class="mb-4 p-2 bg-blue-50 rounded border border-blue-100">
        <span class="font-medium text-blue-800">关联事件：</span>
        <!-- 直接显示，即使为空也显示“无”，方便调试 -->
        <a 
          @click="switchToEventView(currentGraphEvent)"
          class="text-primary hover:text-primary/80 hover:underline cursor-pointer"
        >
          {{ currentGraphEvent || '无关联事件' }}
        </a>
      </div>
        <div class="text-gray-700 mb-3">
          {{ originalTweet.results[0].src_v.content }}
        </div>
        <div class="flex flex-wrap gap-4 text-sm text-gray-500">
          <div><span class="font-medium">发布者:</span> {{ originalTweet.results[0].src_v.uname }}</div>
          <div><span class="font-medium">发布时间:</span> {{ formatDate(originalTweet.results[0].src_v.publishtimestamp) }}</div>
          <div v-if="originalTweet.results[0].src_v.isrumor !== null" class="flex items-center">
            <span class="font-medium">类型:</span>
            <span 
              :class="{
                'bg-green-100 text-green-800 ml-1': !originalTweet.results[0].src_v.isrumor,
                'bg-red-100 text-red-800 ml-1': originalTweet.results[0].src_v.isrumor
              }" 
              class="text-xs px-2 py-0.5 rounded font-medium"
            >
              {{ originalTweet.results[0].src_v.isrumor ? '谣言' : '真实' }}
            </span>
          </div>
        </div>
        <!-- 图片展示 -->
        <div v-if="originalTweet.results[0].src_v.pics_url" class="mt-4">
          <h5 class="text-sm font-medium text-gray-700 mb-2">图片:</h5>
          <div class="flex flex-wrap gap-2">
            <img 
              v-for="(url, index) in originalTweet.results[0].src_v.pics_url.split(', ')" 
              :key="index" 
              :src="url" 
              class="max-h-40 max-w-40 object-cover rounded-md border border-gray-200"
              alt="推文图片"
            >
          </div>
        </div>
      </div>

      <!-- 图谱加载状态 -->
      <div v-if="loadingGraph" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="mt-2 text-gray-500">正在加载传播图谱...</p>
      </div>
      
      <!-- 图谱内容 -->
      <div v-else>
        <!-- 有数据时显示图 -->
        <div v-if="hasSearched && relatedData && relatedData.results && relatedData.results.length > 0">
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
            
            <div v-if="selectedNode.publishtimestamp || selectedNode.republishtime" class="text-sm text-gray-500 mt-1">
                {{ formatDate(selectedNode.publishtimestamp || selectedNode.republishtime) }}
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
        
        <!-- 无数据时显示提示 - 修改：只有加载过数据后才显示 -->
        <div v-if="hasSearched && (!relatedData || !relatedData.results || relatedData.results.length === 0)" class="text-center py-8 border border-dashed border-gray-200 rounded-lg">
          <i class="fa fa-search-minus text-gray-300 text-4xl mb-2"></i>
          <p class="text-gray-500">未找到与 "{{ currentGraphId }}" 相关的图谱数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  import { ref, watch, nextTick, onMounted } from 'vue';
  import * as echarts from 'echarts';
  import { getGraphDataById } from '../../service/apiManager.js';
  import { getOriginalTweetById } from '../../service/apiManager.js';
  import { formatDate } from '../../utils/date.js';
  import { useRouter } from 'vue-router';
  export default {
    name: 'PathView',
    props: {
      initialGraphId: {
        type: String,
        default: ''
      },
      // 新增：接收事件名称prop
      initialGraphEvent: {
        type: String,
        default: ''
      }
    },
    
    emits: ['clearGraph'],
    setup(props, { emit }) {
      // 新增：标记是否已执行过搜索
      const hasSearched = ref(false);
      // 图谱相关变量
      const currentGraphId = ref(props.initialGraphId);
      const currentGraphEvent = ref(props.initialGraphEvent);
      const relatedData = ref(null);
      const loadingGraph = ref(false);
      const chart = ref(null);
      const selectedNode = ref(null);
      const chartContainer = ref(null);
      const isDataReady = ref(false);
      const isContainerReady = ref(false);
      const errorMessage = ref('');
      const originalTweet = ref(null);
      const router = useRouter();
      // 监听初始图谱ID变化
      watch(() => props.initialGraphId, (newId) => {
        if (newId && newId !== currentGraphId.value) {
          console.log('从路由参数接收推文ID:', newId);
          currentGraphId.value = newId;
          loadGraphData(newId); // 自动加载数据
        }
      },
      { immediate: true } // 初始化时立即执行
      );

      // 确保在组件挂载时执行一次查询
      onMounted(() => {
        if (props.initialGraphId) {
          console.log('组件挂载时检测到初始ID:', props.initialGraphId);
          loadGraphData(props.initialGraphId);
        }
      });
      // 新增：监听初始事件名称变化
      watch(() => props.initialGraphEvent, (newEvent) => {
        currentGraphEvent.value = newEvent;
      });

      // 点击关联事件跳转方法
      const switchToEventView = (newEvent) => {
        console.log('点击关联事件，事件数据:', newEvent);
        if (!newEvent) return; // 确保事件名称存在
        // 跳转到EventView，携带事件ID和必要参数
        router.push({
          path: '/event',
          query:{ event: newEvent }
        });
      };

      // 时间格式化
      const formatDate = (timestamp) => {
        if (!timestamp) return '';
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
      
      // 加载图谱数据和推文原文
      const loadGraphData = async (Id) => {
        if (!Id) return;
        
        loadingGraph.value = true;
        errorMessage.value = '';
        // 标记为已搜索
        hasSearched.value = true;
        try {
          // 并行请求图谱数据和推文原文
          const [graphResponse, tweetResponse] = await Promise.all([
            getGraphDataById(Id),
            getOriginalTweetById(Id)
          ]);
          
          // 清空旧数据
          relatedData.value = null;
          originalTweet.value = null;
          await nextTick();
          
          // 更新数据
          relatedData.value = graphResponse.data;
          originalTweet.value = tweetResponse.data;
          
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
      
      // 清除图谱显示
      const clearGraph = () => {
        currentGraphId.value = '';
        relatedData.value = null;
        selectedNode.value = null;
        originalTweet.value = null;
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
      
      // 其余代码保持不变...
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
      
      const handleError = (error) => {
        if (error.response) {
          console.error(`请求失败 (${error.response.status}):`, error.response.data);
        } else if (error.request) {
          console.error("没有收到服务器响应:", error.request);
        } else {
          console.error("请求错误:", error.message);
        }
      };
      
      const drawGraph = () => {
        if (!chartContainer.value || !relatedData.value?.results || !currentGraphId.value) {
          console.error('Chart container or data not found');
          return;
        }
        
        if (chart.value) {
          chart.value.dispose();
        }
        
        chart.value = echarts.init(chartContainer.value);
        
        const nodes = new Map();
        const links = [];
        const nodeTypes = new Map();
        let nextCategoryId = 0;
        
        const centerId = currentGraphId.value;
        
        nodes.set(centerId, {
          id: centerId,
          name: '推文原文',
          symbolSize: 60,
          itemStyle: { color: '#FBBC05' },
          category: 0,
          draggable: true,
          originalData: { vid: centerId, type: 'Original_Tweet' }
        });
        nodeTypes.set('Original_Tweet', 0);
        nextCategoryId = 1;
        
        relatedData.value.results.forEach((item) => {
          if (!item.e_src) {
            console.warn('跳过无效边数据:', item);
            return;
          }

          const srcNodeType = item.src_type || 'Unknown';
          const srcNodeProps = item.src_props || {};

          let source = item.e_src;
          let target;
          
          if (item.e_type === 'belong') {
            target = centerId;
          } else if (item.e_type === 'forwarded') {
            if (!item.e_dst) return;
            target = item.e_dst;
          } else {
            return;
          }

          if (!nodes.has(source)) {
            const finalSrcType = srcNodeType === 'Original_Tweet' ? 'Unknown' : srcNodeType;

            if (!nodeTypes.has(finalSrcType)) {
              nodeTypes.set(finalSrcType, nextCategoryId);
              nextCategoryId++;
            }
            
            let nodeName;
            if (srcNodeProps.content) {
              nodeName = srcNodeProps.content.substring(0, 8) + '...';
            } else if (srcNodeProps.retext) {
              nodeName = srcNodeProps.retext.substring(0, 8) + '...';
            } else if (srcNodeProps.title) {
              nodeName = srcNodeProps.title.substring(0, 8) + '...';
            } else {
              nodeName = '推文原文';
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

          if (item.e_type === 'forwarded' && !nodes.has(target)) {
            const dstNodeType = item.dst_type || 'Unknown';
            const dstNodeProps = item.dst_props || {};
            
            const finalDstType = dstNodeType === 'Original_Tweet' ? 'Unknown' : dstNodeType;

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
        
        chart.value.on('click', (params) => {
          if (params.dataType === 'node') {
            if (params.data.originalData?.type === 'Original_Tweet') {
              window.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
              selectedNode.value = params.data.originalData;
            }
          }
        });
        
        window.addEventListener('resize', () => {
          if (chart.value) {
            chart.value.resize();
          }
        });
      };

      const getNodeColorByType = (type) => {
        const colorMap = {
          'Event': '#1890ff',
          'Article': '#34A853',
          'Original_Tweet': '#FBBC05',
          'Retweet': '#F2994A',
          'User': '#9B51E0',
          'Comment': '#EA4335',
          'Unknown': '#8884d8'
        };
        return colorMap[type] || colorMap['Unknown'];
      };
      
      const getNodeSizeByType = (type) => {
        const sizeMap = {
          'Event': 50,
          'Article': 40,
          'Original_Tweet': 40,
          'Retweet': 30,
          'User': 30,
          'Comment': 30,
          'Unknown': 35
        };
        return sizeMap[type] || sizeMap['Unknown'];
      };

      const closeNodeDetail = () => {
        selectedNode.value = null;
      };
      
      const getNodeTitle = (node) => {
        return node.title ||  '转发节点';
      };
      
      const getNodeType = (node) => {
        return node.type || node.e_type || '未知类型';
      };


      
      return {
        currentGraphId,
        relatedData,
        loadingGraph,
        chart,
        selectedNode,
        chartContainer,
        errorMessage,
        loadGraphData,
        clearGraph,
        closeNodeDetail,
        getNodeTitle,
        getNodeType,
        formatDate,
        originalTweet,
        currentGraphEvent,  // 导出事件名称变量
        switchToEventView,
        hasSearched  // 导出新增的状态变量
      };
    }
  };
</script>