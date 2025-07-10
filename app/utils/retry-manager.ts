export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
  retryCondition?: (error: any) => boolean;
  onRetry?: (attempt: number, error: any) => void;
  onMaxRetriesReached?: (error: any) => void;
}

export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: any;
  attempts: number;
  totalTime: number;
}

export class RetryManager {
  private static defaultConfig: RetryConfig = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
    backoffFactor: 2,
    retryCondition: (error: any) => {
      // 默认重试条件：网络错误、超时、5xx服务器错误
      if (error instanceof Error) {
        const message = error.message.toLowerCase();
        return (
          message.includes("network") ||
          message.includes("timeout") ||
          message.includes("连接失败") ||
          message.includes("服务器内部错误")
        );
      }

      // HTTP状态码重试条件
      if (error.status) {
        return (
          error.status >= 500 || error.status === 408 || error.status === 429
        );
      }

      return false;
    },
  };

  /**
   * 执行带重试的异步操作
   */
  static async executeWithRetry<T>(
    operation: () => Promise<T>,
    config: Partial<RetryConfig> = {},
  ): Promise<RetryResult<T>> {
    const finalConfig = { ...this.defaultConfig, ...config };
    const startTime = Date.now();
    let lastError: any;
    let attempts = 0;

    for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
      attempts = attempt + 1;

      try {
        const result = await operation();
        return {
          success: true,
          data: result,
          attempts,
          totalTime: Date.now() - startTime,
        };
      } catch (error) {
        lastError = error;

        // 如果是最后一次尝试，不再重试
        if (attempt === finalConfig.maxRetries) {
          break;
        }

        // 检查是否应该重试
        if (finalConfig.retryCondition && !finalConfig.retryCondition(error)) {
          break;
        }

        // 调用重试回调
        if (finalConfig.onRetry) {
          finalConfig.onRetry(attempt + 1, error);
        }

        // 计算延迟时间（指数退避）
        const delay = Math.min(
          finalConfig.baseDelay * Math.pow(finalConfig.backoffFactor, attempt),
          finalConfig.maxDelay,
        );

        // 添加随机抖动（避免雷群效应）
        const jitteredDelay = delay + Math.random() * 1000;

        await this.sleep(jitteredDelay);
      }
    }

    // 达到最大重试次数
    if (finalConfig.onMaxRetriesReached) {
      finalConfig.onMaxRetriesReached(lastError);
    }

    return {
      success: false,
      error: lastError,
      attempts,
      totalTime: Date.now() - startTime,
    };
  }

  /**
   * 创建一个可取消的重试操作
   */
  static createCancellableRetry<T>(
    operation: (signal: AbortSignal) => Promise<T>,
    config: Partial<RetryConfig> = {},
  ) {
    const controller = new AbortController();

    const promise = this.executeWithRetry(
      () => operation(controller.signal),
      config,
    );

    return {
      promise,
      cancel: () => controller.abort(),
      signal: controller.signal,
    };
  }

  /**
   * 智能重试：根据错误类型自动调整重试策略
   */
  static async smartRetry<T>(
    operation: () => Promise<T>,
    customConfig: Partial<RetryConfig> = {},
  ): Promise<RetryResult<T>> {
    // 先尝试一次快速重试
    const quickConfig: Partial<RetryConfig> = {
      maxRetries: 1,
      baseDelay: 500,
      backoffFactor: 1,
      ...customConfig,
    };

    const quickResult = await this.executeWithRetry(operation, quickConfig);

    if (quickResult.success) {
      return quickResult;
    }

    // 如果快速重试失败，使用标准重试策略
    const standardConfig: Partial<RetryConfig> = {
      maxRetries: 3,
      baseDelay: 2000,
      backoffFactor: 2,
      maxDelay: 15000,
      ...customConfig,
    };

    return this.executeWithRetry(operation, standardConfig);
  }

  /**
   * 批量重试：对多个操作进行重试
   */
  static async batchRetry<T>(
    operations: (() => Promise<T>)[],
    config: Partial<RetryConfig> = {},
  ): Promise<RetryResult<T>[]> {
    const promises = operations.map((op) => this.executeWithRetry(op, config));
    return Promise.all(promises);
  }

  /**
   * 条件重试：只有满足特定条件时才重试
   */
  static async conditionalRetry<T>(
    operation: () => Promise<T>,
    condition: (error: any, attempt: number) => boolean,
    config: Partial<RetryConfig> = {},
  ): Promise<RetryResult<T>> {
    const enhancedConfig = {
      ...config,
      retryCondition: (error: any) => {
        const baseCondition =
          config.retryCondition?.(error) ??
          this.defaultConfig.retryCondition!(error);
        return baseCondition && condition(error, 0);
      },
    };

    return this.executeWithRetry(operation, enhancedConfig);
  }

  private static sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * 获取错误的重试建议
   */
  static getRetryRecommendation(error: any): {
    shouldRetry: boolean;
    suggestedDelay: number;
    reason: string;
  } {
    if (error instanceof Error) {
      const message = error.message.toLowerCase();

      if (message.includes("timeout")) {
        return {
          shouldRetry: true,
          suggestedDelay: 3000,
          reason: "请求超时，建议重试",
        };
      }

      if (message.includes("network") || message.includes("连接失败")) {
        return {
          shouldRetry: true,
          suggestedDelay: 2000,
          reason: "网络连接问题，建议重试",
        };
      }

      if (message.includes("服务器内部错误")) {
        return {
          shouldRetry: true,
          suggestedDelay: 5000,
          reason: "服务器错误，建议稍后重试",
        };
      }

      if (message.includes("会话已过期")) {
        return {
          shouldRetry: true,
          suggestedDelay: 1000,
          reason: "会话过期，将自动重新初始化",
        };
      }
    }

    return {
      shouldRetry: false,
      suggestedDelay: 0,
      reason: "不建议重试此类错误",
    };
  }
}

// 预设的重试配置
export const RetryPresets = {
  // 网络请求重试
  network: {
    maxRetries: 3,
    baseDelay: 1000,
    backoffFactor: 2,
    maxDelay: 10000,
  } as Partial<RetryConfig>,

  // 文件上传重试
  upload: {
    maxRetries: 5,
    baseDelay: 2000,
    backoffFactor: 1.5,
    maxDelay: 30000,
  } as Partial<RetryConfig>,

  // 快速重试（用于轻量级操作）
  quick: {
    maxRetries: 2,
    baseDelay: 500,
    backoffFactor: 1.5,
    maxDelay: 2000,
  } as Partial<RetryConfig>,

  // 长时间重试（用于重要操作）
  persistent: {
    maxRetries: 10,
    baseDelay: 3000,
    backoffFactor: 1.8,
    maxDelay: 60000,
  } as Partial<RetryConfig>,
};
