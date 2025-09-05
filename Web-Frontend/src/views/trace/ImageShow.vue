<template>
  <!-- 半透明背景层，点击可关闭 -->
  <div class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50" @click="$emit('close')">
    <!-- 图片容器，阻止事件冒泡 -->
    <div class="relative max-w-full p-4" @click.stop>
      <h1 class="text-xl font-bold mb-6 text-white">图片详情</h1>
      <!-- 图片显示区域 -->
      <div v-if="imageData" class="max-w-full">
        <img 
          :src="imageData" 
          alt="预览图片" 
          class="max-w-full h-auto rounded-lg shadow-md"
        />
      </div>
      <div v-else>
        <p class="text-gray-300">无图片数据</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  // 接收父组件传入的图片URL
  props: {
    imageUrl: String,
    showClose: { // 新增属性
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      imageData: null // 存储图片数据
    };
  },
  created() {
    // 优先使用props传入的URL，回退使用localStorage
    this.imageData = this.imageUrl || localStorage.getItem('tempImage');
    // 如果使用了localStorage数据，使用后清理缓存
    if (!this.imageUrl) {
      localStorage.removeItem('tempImage');
    }
  }
};
</script>