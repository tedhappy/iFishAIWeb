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

// 判断是否启用日志输出
// 通过NEXT_PUBLIC_ENABLE_LOGGING环境变量控制：true启用，false禁用
// 如果未设置该变量，则回退到原有逻辑（通过API_BASE_URL判断）
function isLoggingEnabled(): boolean {
  try {
    // 在服务器端渲染时，process.env 可能不可用
    if (typeof process === "undefined") {
      return true; // 默认启用日志
    }

    // 优先检查专门的日志控制环境变量
    const enableLogging = process.env.NEXT_PUBLIC_ENABLE_LOGGING;
    if (enableLogging !== undefined) {
      return enableLogging.toLowerCase() === "true";
    }

    // 如果没有设置日志控制变量，回退到原有逻辑
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const isDev =
      apiBaseUrl.includes("localhost") || apiBaseUrl.includes("127.0.0.1");
    return isDev; // 开发环境启用日志，生产环境禁用
  } catch (error) {
    // 如果出现任何错误，默认启用日志以确保调试可见
    return true;
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
      if (isLoggingEnabled()) {
        const consoleObj = safeConsole();
        consoleObj?.log(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  error: (...args: any[]) => {
    try {
      if (isLoggingEnabled()) {
        const consoleObj = safeConsole();
        consoleObj?.error(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  warn: (...args: any[]) => {
    try {
      if (isLoggingEnabled()) {
        const consoleObj = safeConsole();
        consoleObj?.warn(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  info: (...args: any[]) => {
    try {
      if (isLoggingEnabled()) {
        const consoleObj = safeConsole();
        consoleObj?.info(`[${getTimestamp()}]`, ...args);
      }
    } catch (error) {
      // 静默处理日志错误，避免影响应用运行
    }
  },

  debug: (...args: any[]) => {
    try {
      if (isLoggingEnabled()) {
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
