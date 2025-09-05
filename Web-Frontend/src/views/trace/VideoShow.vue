<template>
  <!-- 半透明背景层，点击可关闭 -->
  <div class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50" @click="$emit('close')">
    <!-- 视频容器，阻止事件冒泡 -->
    <div class="relative max-w-full p-4" @click.stop>
      <h1 class="text-xl font-bold mb-6 text-white">视频详情</h1>
      <!-- 视频显示区域 -->
      <div v-if="videoData">
        <video controls class="max-w-full h-auto rounded-lg shadow-md">
          <source :src="videoData" type="video/mp4">
          您的浏览器不支持视频播放
        </video>
      </div>
      <div v-else>
        <p class="text-gray-300">无视频数据</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  // 接收父组件传入的视频URL
  props: {
    videoUrl: String,
    showClose: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      videoData: null // 存储视频数据
    };
  },
  created() {
    // 优先使用props传入的URL，回退使用localStorage
    this.videoData = this.videoUrl;
    // 如果使用了localStorage数据，使用后清理缓存
    if (!this.videoUrl) {
      localStorage.removeItem('tempVideo');
    }
  }
};
</script>