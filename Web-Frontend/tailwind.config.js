// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6', // 蓝色（默认主题色）
        // 或自定义颜色
        primary: '#165DFF',
      },
    },
  },
  plugins: [],
}