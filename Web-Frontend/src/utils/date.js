/**
 * 格式化日期时间戳为本地日期时间字符串
 * @param {number} timestamp - 时间戳（毫秒）
 * @returns {string} 格式化后的日期时间字符串
 */
export function formatDate(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

/**
 * 格式化日期时间戳为相对时间描述（例如：几分钟前、几小时前等）
 * @param {number} timestamp - 时间戳（毫秒）
 * @returns {string} 相对时间描述
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return '';
  
  const now = new Date().getTime();
  const diff = now - timestamp;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) {
    return `${days}天前`;
  } else if (hours > 0) {
    return `${hours}小时前`;
  } else if (minutes > 0) {
    return `${minutes}分钟前`;
  } else {
    return '刚刚';
  }
}

/**
 * 格式化日期时间戳为 YYYY-MM-DD 格式
 * @param {number} timestamp - 时间戳（毫秒）
 * @returns {string} YYYY-MM-DD 格式日期字符串
 */
export function formatDateString(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
}