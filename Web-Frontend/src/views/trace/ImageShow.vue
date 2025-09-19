<template>
  <!-- 半透明背景层 -->
  <div class="fixed inset-0 bg-black bg-opacity-70 flex items-start justify-center z-50 pt-12" @click="$emit('close')">
    <!-- 固定大小的图片容器，阻止事件冒泡 -->
    <div class="relative bg-gray-900 rounded-lg shadow-2xl w-[90vw] h-[80vh] max-w-6xl p-6 transform -translate-y-2" @click.stop>
      
      <!-- 标题和计数器一起居中 -->
      <div class="text-center mb-4">
        <h1 class="text-xl font-bold text-white inline-block mr-2">图片详情</h1>
        <span v-if="imageList.length > 1" class="text-gray-300 text-lg">
          ({{ currentIndex + 1 }}/{{ imageList.length }})
        </span>
      </div>

      <!-- 图片显示区域 - 固定大小容器 -->
      <div v-if="imageList.length > 0" class="relative flex items-center justify-center h-[calc(90vh-120px)] bg-black rounded-lg">
        <!-- 左箭头按钮 -->
        <button 
          v-if="imageList.length > 1"
          @click="prevImage"
          class="absolute left-4 z-10 bg-black bg-opacity-50 text-white p-3 rounded-full hover:bg-opacity-70 transition-all"
          :class="{ 'opacity-50 cursor-not-allowed': currentIndex === 0 }"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
        </button>

        <!-- 图片显示 - 在固定容器内 -->
        <div class="flex items-center justify-center w-full h-full overflow-hidden">
          <img 
            :src="imageList[currentIndex]" 
            alt="预览图片"
            class="max-w-full max-h-full object-contain transition-opacity duration-300"
            :class="{ 'opacity-0': !imageLoaded }"
            @load="imageLoaded = true"
          />
          <!-- 加载指示器 -->
          <div v-if="!imageLoaded" class="absolute inset-0 flex items-center justify-center">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          </div>
        </div>

        <!-- 右箭头按钮 -->
        <button 
          v-if="imageList.length > 1"
          @click="nextImage"
          class="absolute right-4 z-10 bg-black bg-opacity-50 text-white p-3 rounded-full hover:bg-opacity-70 transition-all"
          :class="{ 'opacity-50 cursor-not-allowed': currentIndex === imageList.length - 1 }"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>

      <!-- 缩略图导航 -->
      <div v-if="imageList.length > 1" class="flex justify-center mt-4 space-x-2 overflow-x-auto py-2">
        <button 
          v-for="(url, index) in imageList" 
          :key="index"
          @click="currentIndex = index"
          class="flex-shrink-0 w-16 h-16 border-2 rounded overflow-hidden transition-all"
          :class="{
            'border-blue-500 scale-105': currentIndex === index,
            'border-gray-600': currentIndex !== index
          }"
        >
          <img :src="url" alt="缩略图" class="w-full h-full object-cover" />
        </button>
      </div>

      <div v-else class="h-[calc(90vh-120px)] flex items-center justify-center bg-black rounded-lg">
        <p class="text-gray-400">无图片数据</p>
      </div>

      <!-- 关闭按钮 -->
      <button 
        @click="$emit('close')"
        class="absolute top-4 right-4 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-70 transition-all"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  // 接收父组件传入的图片URL
  props: {
    imageUrl: String,
    showClose: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      imageData: null,
      currentIndex: 0,
      imageLoaded: false
    };
  },
  computed: {
    // 将分号分隔的图片URL转换为数组
    imageList() {
      if (!this.imageData) return [];
      return this.imageData.split(';').filter(url => url.trim());
    }
  },
  created() {
    // 优先使用props传入的URL，回退使用localStorage
    this.imageData = this.imageUrl || localStorage.getItem('tempImage');
    // 如果使用了localStorage数据，使用后清理缓存
    if (!this.imageUrl) {
      localStorage.removeItem('tempImage');
    }
  },
  methods: {
    // 上一张图片
    prevImage() {
      if (this.currentIndex > 0) {
        this.currentIndex--;
        this.imageLoaded = false;
      }
    },
    // 下一张图片
    nextImage() {
      if (this.currentIndex < this.imageList.length - 1) {
        this.currentIndex++;
        this.imageLoaded = false;
      }
    },
    // 键盘导航支持
    handleKeydown(event) {
      if (event.key === 'ArrowLeft') {
        this.prevImage();
      } else if (event.key === 'ArrowRight') {
        this.nextImage();
      } else if (event.key === 'Escape') {
        this.$emit('close');
      }
    }
  },
  mounted() {
    // 添加键盘事件监听
    window.addEventListener('keydown', this.handleKeydown);
  },
  beforeUnmount() {
    // 移除键盘事件监听
    window.removeEventListener('keydown', this.handleKeydown);
  }
};
</script>

<style scoped>
/* 确保固定尺寸 */
.fixed-container {
  width: 90vw;
  height: 90vh;
  max-width: 1200px;
  max-height: 800px;
}

.image-area {
  height: calc(90vh - 120px);
}
</style>