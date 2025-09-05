const { defineConfig } = require('@vue/cli-service')
module.exports = {
  lintOnSave: false,
  devServer: {
    proxy: {
      '/api': {
        target: 'http://192.168.10.1:5000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      }
    }
  }
  // content: [
  //   "./src/**/*.{vue,js,ts,jsx,tsx}",
  // ],
  // theme: {
  //   extend: {
  //     colors: {
  //       primary: '#3B82F6', // 蓝色（默认主题色）
  //       // 或自定义颜色
  //       primary: '#165DFF',
  //     },
  //   },
  // },
}