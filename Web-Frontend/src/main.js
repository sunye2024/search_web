import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import axios from 'axios'
import { createPinia } from 'pinia'
// 导入API管理器
import apiManager from "./service/apiManager"

// 创建Pinia实例
const pinia = createPinia();

const app = createApp(App)

app.use(router)
app.use(pinia)

// 将API管理器添加到全局属性
app.config.globalProperties.$axios = axios
app.config.globalProperties.$api = apiManager
app.mount('#app')