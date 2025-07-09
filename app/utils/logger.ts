/**
 * 统一日志工具，为所有日志添加时间戳
 * 在生产环境中自动禁用日志输出以提高安全性
 */

// 获取格式化的当前时间（本地时间）
function getTimestamp(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

// 判断是否为生产环境
// 通过NEXT_PUBLIC_API_BASE_URL判断：如果包含localhost或127.0.0.1则为开发环境
function isProduction(): boolean {
  try {
    // 在服务器端渲染时，process.env 可能不可用
    if (typeof process === "undefined") {
      return false; // 默认为开发环境
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const isDev =
      apiBaseUrl.includes("localhost") || apiBaseUrl.includes("127.0.0.1");
    return !isDev;
  } catch (error) {
    // 如果出现任何错误，默认为开发环境以确保日志可见
    return false;
  }
}

// 安全的控制台访问函数
function safeConsole() {
  try {
    return typeof console !== "undefined" ? console : null;
  } catch {
    return null;
  }
}

// 创建带时间戳和环境控制的日志函数
export const logger = {
  log: (...args: any[]) => {
    try {
      if (!isProduction()) {
        const consoleObj = safeConsole();
        consoleObj?.log(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  error: (...args: any[]) => {
    try {
      if (!isProduction()) {
        const consoleObj = safeConsole();
        consoleObj?.error(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  warn: (...args: any[]) => {
    try {
      if (!isProduction()) {
        const consoleObj = safeConsole();
        consoleObj?.warn(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  info: (...args: any[]) => {
    try {
      if (!isProduction()) {
        const consoleObj = safeConsole();
        consoleObj?.info(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  debug: (...args: any[]) => {
    try {
      if (!isProduction()) {
        const consoleObj = safeConsole();
        consoleObj?.debug(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },
};

// 为了向后兼容，也导出单独的函数
export const logWithTime = logger.log;
export const errorWithTime = logger.error;
export const warnWithTime = logger.warn;
export const infoWithTime = logger.info;
export const debugWithTime = logger.debug;
