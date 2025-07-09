import { useAppConfig } from "../store/config";
import { logger } from "./logger";

/**
 * 配置初始化器
 * 在应用启动时调用，用于从环境变量更新默认配置
 */
export class ConfigInitializer {
  private static initialized = false;

  /**
   * 初始化配置
   * 只会执行一次，确保不会重复初始化
   */
  static async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      logger.log(
        "[Config Initializer] Initializing default config from environment variables...",
      );

      // 获取配置store实例
      const configStore = useAppConfig.getState();

      // 更新默认配置
      await configStore.updateDefaultConfig();

      this.initialized = true;
      logger.log(
        "[Config Initializer] Default config initialized successfully",
      );
    } catch (error) {
      logger.error(
        "[Config Initializer] Failed to initialize default config:",
        error,
      );
    }
  }

  /**
   * 重置初始化状态（主要用于测试）
   */
  static reset() {
    this.initialized = false;
  }
}
