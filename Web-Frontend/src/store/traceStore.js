import { defineStore } from 'pinia'

// 创建溯源查询结果的store
export const useTraceStore = defineStore('trace', {
  state: () => ({
    results: [],         // 查询结果数据
    currentPage: 1,      // 当前页码
    itemsPerPage: 10,    // 每页显示数量
    selectedPlatform: '', // 选中的平台筛选条件
    loading: false,      // 加载状态
    errorMessage: ''     // 错误信息
  }),

  getters: {
    // 根据选中的平台筛选结果
    filteredResults(state) {
      if (!state.selectedPlatform) {
        console.log('没有选中平台，返回所有结果');
        return state.results
      }
      
      // 调试信息
      console.log(`筛选平台: ${state.selectedPlatform}`);
      console.log(`原始数据量: ${state.results.length}`);
      
      // 同时检查platform和datasource字段，并支持大小写不敏感匹配
      const filtered = state.results.filter(item => {
        // 获取平台值并转为小写进行比较
        const itemPlatform = (item.platform || '').toLowerCase();
        const itemDatasource = (item.datasource || '').toLowerCase();
        const selectedPlatform = state.selectedPlatform.toLowerCase();
        
        // 调试单个项目的平台信息
        if (itemPlatform.includes('微博') || itemDatasource.includes('微博')) {
          console.log(`找到微博相关项目: platform=${itemPlatform}, datasource=${itemDatasource}`);
        }
        
        // 匹配任何一个字段，使用更宽松的匹配逻辑
        const matches = itemPlatform === selectedPlatform || 
                       itemDatasource === selectedPlatform ||
                       itemPlatform.includes(selectedPlatform) ||
                       itemDatasource.includes(selectedPlatform);
                        
        return matches;
      });
      
      // 输出筛选结果信息
      console.log(`筛选后数据量: ${filtered.length}`);
      
      return filtered;
    },

    // 计算总页数
    totalPages(state) {
      return Math.ceil(state.filteredResults.length / state.itemsPerPage)
    },

    // 当前页显示的结果
    paginatedResults(state) {
      const startIndex = (state.currentPage - 1) * state.itemsPerPage
      const endIndex = startIndex + state.itemsPerPage
      return state.filteredResults.slice(startIndex, endIndex)
    }
  },

  actions: {
    // 设置查询结果
    setResults(data) {
      this.results = data
      this.currentPage = 1  // 重置到第一页
    },

    // 设置当前页码
    setCurrentPage(page) {
      this.currentPage = page
    },

    // 上一页
    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--
        return true
      }
      return false
    },

    // 下一页
    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++
        return true
      }
      return false
    },

    // 重置分页
    resetPagination() {
      this.currentPage = 1
      this.results = []
    },

    // 设置平台筛选条件
    setSelectedPlatform(platform) {
      this.selectedPlatform = platform
      this.currentPage = 1  // 重置到第一页
    },

    // 设置加载状态
    setLoading(loading) {
      this.loading = loading
    },

    // 设置错误信息
    setErrorMessage(message) {
      this.errorMessage = message
    }
  }
})