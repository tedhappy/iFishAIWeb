import { NextRequest, NextResponse } from "next/server";
import { getServerSideConfig } from "../../config/server";
import { ServiceProvider } from "../../constant";

/**
 * 获取默认配置的API端点
 * 返回从环境变量中读取的默认模型和提供商配置
 */
export async function GET(req: NextRequest) {
  try {
    const serverConfig = getServerSideConfig();

    // 从环境变量获取默认配置，如果没有设置则使用fallback值
    const defaultModel = serverConfig.defaultModel || "qwen-turbo-latest";
    const defaultProvider = serverConfig.defaultProvider || "Alibaba";

    // 验证提供商是否有效
    const validProvider = Object.values(ServiceProvider).includes(
      defaultProvider as ServiceProvider,
    )
      ? (defaultProvider as ServiceProvider)
      : ServiceProvider.Alibaba;

    return NextResponse.json({
      defaultModel,
      defaultProvider: validProvider,
    });
  } catch (error) {
    console.error("[Default Config API] Error:", error);
    return NextResponse.json(
      {
        error: "Failed to get default config",
        defaultModel: "qwen-turbo-latest",
        defaultProvider: ServiceProvider.Alibaba,
      },
      { status: 500 },
    );
  }
}
