import axios from 'axios';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api', // 后端 API 基础 URL
  timeout: 20000, // 请求超时时间
});

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么，例如添加认证 token
    // config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  error => {
    // 对请求错误做些什么
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    // 对响应数据做些什么
    return response;
  },
  error => {
    // 对响应错误做些什么
    if (error.response) {
      // 服务器返回了错误状态码
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('Network Error:', error.request);
    } else {
      // 其他错误
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API 请求函数
// 文本溯源查询
export const searchTraceByText = (queryContent, threshold) => {
  return apiClient.post('/search/text', new URLSearchParams({
    queryContent,
    threshold
  }), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
};

// 图片溯源查询
export const searchTraceByImage = (file, topk) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('topk', topk);
  return apiClient.post('/search/picture', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

// 视频溯源查询
export const searchTraceByVideo = (file, topk, config = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('topk', topk);
  return apiClient.post('/search/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config  // 添加配置参数
  });
};

// 上传文件
export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

// 通过 ID 获取推文数据
export const getOriginalTweetById = (id, space_name = 'Social_Network_1') => {
  return apiClient.get('/getOriginalTweetById', {
    params: { id, space_name }
  });
};

// 通过 ID 获取关联图谱数据
export const getGraphDataById = (id, space_name = 'Social_Network_1') => {
  return apiClient.get('/getRelatedById', {
    params: { id, space_name }
  });
};

// 通过事件名称获取关联图谱数据
export const getGraphDataByEvent = (event, space_name = 'Social_Network_1') => {
  return apiClient.get('/getRelatedByEvent', {
    params: { event, space_name }
  });
};

// 导出 axios 实例以供直接使用
export default apiClient;