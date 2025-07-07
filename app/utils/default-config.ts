import { ServiceProvider } from "../constant";

/**
 * 默认配置接口
 */
export interface DefaultConfig {
  defaultModel: string;
  defaultProvider: ServiceProvider;
}

/**
 * 从服务器获取默认配置
 * 如果在服务器端，直接从环境变量读取
 * 如果在客户端，通过API调用获取
 */
export async function getDefaultConfig(): Promise<DefaultConfig> {
  // 服务器端直接读取环境变量
  if (typeof window === "undefined") {
    // 直接从process.env读取，避免循环依赖
    const defaultModel = process.env.DEFAULT_MODEL || "qwen-turbo-latest";
    const defaultProvider = process.env.DEFAULT_PROVIDER || "Alibaba";

    // 验证提供商是否有效
    const validProvider = Object.values(ServiceProvider).includes(
      defaultProvider as ServiceProvider,
    )
      ? (defaultProvider as ServiceProvider)
      : ServiceProvider.Alibaba;

    return {
      defaultModel,
      defaultProvider: validProvider,
    };
  }

  // 客户端通过API获取
  try {
    const response = await fetch("/api/default-config");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const config = await response.json();
    return {
      defaultModel: config.defaultModel || "qwen-turbo-latest",
      defaultProvider: config.defaultProvider || ServiceProvider.Alibaba,
    };
  } catch (error) {
    console.error("[Default Config] Failed to fetch default config:", error);
    // 返回fallback配置
    return {
      defaultModel: "qwen-turbo-latest",
      defaultProvider: ServiceProvider.Alibaba,
    };
  }
}

/**
 * 同步获取默认配置（仅用于初始化）
 * 使用硬编码的fallback值，实际配置会在运行时更新
 */
export function getDefaultConfigSync(): DefaultConfig {
  return {
    defaultModel: "qwen-turbo-latest",
    defaultProvider: ServiceProvider.Alibaba,
  };
}
