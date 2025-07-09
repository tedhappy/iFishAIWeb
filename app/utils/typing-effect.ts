/**
 * 打字机效果工具类
 * 提供流畅的文本逐字显示功能
 */

export interface TypingEffectOptions {
  /** 基础打字速度（字符/秒） */
  baseSpeed?: number;
  /** 是否启用自适应速度 */
  adaptiveSpeed?: boolean;
  /** 最大消息长度限制 */
  maxLength?: number;
  /** 重试次数 */
  maxRetries?: number;
  /** 是否启用内存监控 */
  enableMemoryMonitor?: boolean;
}

export interface TypingEffectCallbacks {
  /** 内容更新回调 */
  onUpdate: (content: string) => void;
  /** 完成回调 */
  onComplete: (content: string) => void;
  /** 错误回调 */
  onError: (error: Error) => void;
  /** 中止检查回调 */
  shouldAbort: () => boolean;
}

export class TypingEffect {
  private static readonly DEFAULT_OPTIONS: Required<TypingEffectOptions> = {
    baseSpeed: 30,
    adaptiveSpeed: true,
    maxLength: 50000,
    maxRetries: 3,
    enableMemoryMonitor: true,
  };

  private options: Required<TypingEffectOptions>;
  private abortController: AbortController | null = null;
  private retryCount = 0;

  constructor(options: TypingEffectOptions = {}) {
    this.options = { ...TypingEffect.DEFAULT_OPTIONS, ...options };
  }

  /**
   * 开始打字机效果
   * @param text 要显示的文本
   * @param callbacks 回调函数
   */
  async start(text: string, callbacks: TypingEffectCallbacks): Promise<void> {
    this.abortController = new AbortController();
    this.retryCount = 0;

    try {
      await this.executeTypingEffect(text, callbacks);
    } catch (error) {
      callbacks.onError(error as Error);
    }
  }

  /**
   * 停止打字机效果
   */
  stop(): void {
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  /**
   * 执行打字机效果的核心逻辑
   */
  private async executeTypingEffect(
    originalText: string,
    callbacks: TypingEffectCallbacks,
  ): Promise<void> {
    // 文本长度验证和截断
    let text = originalText;
    if (text.length > this.options.maxLength) {
      console.warn(
        `消息长度超过限制 (${text.length}/${this.options.maxLength})，将截断显示`,
      );
      text = text.substring(0, this.options.maxLength) + "...";
    }

    try {
      // 计算自适应打字速度
      const speed = this.calculateTypingSpeed(text.length);
      const delayPerChar = 1000 / speed;

      // 使用 requestAnimationFrame 实现流畅动画
      await this.animateTyping(text, delayPerChar, callbacks);

      // 完成回调
      callbacks.onComplete(text);
    } catch (error) {
      // 重试机制
      if (this.shouldRetry(error)) {
        this.retryCount++;
        console.log(
          `重试打字机效果 (${this.retryCount}/${this.options.maxRetries})`,
        );

        // 等待后重试
        await this.delay(500);
        await this.executeTypingEffect(originalText, callbacks);
        return;
      }

      throw error;
    } finally {
      // 内存监控
      if (this.options.enableMemoryMonitor) {
        this.checkMemoryUsage();
      }
    }
  }

  /**
   * 计算自适应打字速度
   */
  private calculateTypingSpeed(textLength: number): number {
    if (!this.options.adaptiveSpeed) {
      return this.options.baseSpeed;
    }

    // 根据文本长度动态调整速度
    if (textLength < 100) return Math.max(this.options.baseSpeed, 40);
    if (textLength < 500) return Math.max(this.options.baseSpeed, 50);
    if (textLength < 2000) return Math.max(this.options.baseSpeed, 60);
    return Math.max(this.options.baseSpeed, 80);
  }

  /**
   * 使用 requestAnimationFrame 实现动画
   */
  private animateTyping(
    text: string,
    delayPerChar: number,
    callbacks: TypingEffectCallbacks,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      let currentIndex = 0;
      let lastUpdateTime = performance.now();
      let accumulatedTime = 0;

      const animate = (currentTime: number) => {
        try {
          // 检查是否应该中止
          if (this.abortController?.signal.aborted || callbacks.shouldAbort()) {
            callbacks.onUpdate(text); // 立即显示完整内容
            resolve();
            return;
          }

          // 计算时间差
          const deltaTime = currentTime - lastUpdateTime;
          accumulatedTime += deltaTime;
          lastUpdateTime = currentTime;

          // 根据累积时间决定是否更新字符
          const charactersToAdd = Math.floor(accumulatedTime / delayPerChar);

          if (charactersToAdd > 0) {
            currentIndex = Math.min(
              currentIndex + charactersToAdd,
              text.length,
            );
            accumulatedTime = accumulatedTime % delayPerChar;

            // 更新内容
            callbacks.onUpdate(text.substring(0, currentIndex));
          }

          // 检查是否完成
          if (currentIndex >= text.length) {
            resolve();
            return;
          }

          // 继续动画
          requestAnimationFrame(animate);
        } catch (error) {
          reject(error);
        }
      };

      // 开始动画
      requestAnimationFrame(animate);
    });
  }

  /**
   * 判断是否应该重试
   */
  private shouldRetry(error: any): boolean {
    return (
      this.retryCount < this.options.maxRetries &&
      !this.abortController?.signal.aborted &&
      !(error instanceof DOMException && error.name === "AbortError")
    );
  }

  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * 内存使用监控
   */
  private checkMemoryUsage(): void {
    if (typeof window !== "undefined" && window.performance) {
      const memoryInfo = (performance as any).memory;
      if (memoryInfo && memoryInfo.usedJSHeapSize > 100 * 1024 * 1024) {
        console.warn(
          `检测到内存使用过高: ${Math.round(memoryInfo.usedJSHeapSize / 1024 / 1024)}MB，建议刷新页面`,
        );
      }
    }
  }

  /**
   * 获取当前配置
   */
  getOptions(): Required<TypingEffectOptions> {
    return { ...this.options };
  }

  /**
   * 更新配置
   */
  updateOptions(newOptions: Partial<TypingEffectOptions>): void {
    this.options = { ...this.options, ...newOptions };
  }
}

/**
 * 创建打字机效果实例的工厂函数
 */
export function createTypingEffect(
  options?: TypingEffectOptions,
): TypingEffect {
  return new TypingEffect(options);
}

/**
 * 简化的打字机效果函数，用于快速使用
 */
export async function typeText(
  text: string,
  onUpdate: (content: string) => void,
  options?: TypingEffectOptions,
): Promise<void> {
  const typingEffect = createTypingEffect(options);

  return new Promise((resolve, reject) => {
    typingEffect.start(text, {
      onUpdate,
      onComplete: () => resolve(),
      onError: reject,
      shouldAbort: () => false,
    });
  });
}
