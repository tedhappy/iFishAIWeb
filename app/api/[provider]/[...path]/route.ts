import { ApiPath } from "@/app/constant";
import { NextRequest } from "next/server";
import { logger } from "../../../utils/logger";
import { handle as azureHandler } from "../../azure";
import { handle as googleHandler } from "../../google";
import { handle as anthropicHandler } from "../../anthropic";
import { handle as baiduHandler } from "../../baidu";
import { handle as bytedanceHandler } from "../../bytedance";
import { handle as alibabaHandler } from "../../alibaba";
import { handle as moonshotHandler } from "../../moonshot";
import { handle as stabilityHandler } from "../../stability";
import { handle as iflytekHandler } from "../../iflytek";
import { handle as deepseekHandler } from "../../deepseek";
import { handle as siliconflowHandler } from "../../siliconflow";
import { handle as xaiHandler } from "../../xai";
import { handle as chatglmHandler } from "../../glm";
import { handle as proxyHandler } from "../../proxy";

async function handle(
  req: NextRequest,
  { params }: { params: { provider: string; path: string[] } },
) {
  const apiPath = `/api/${params.provider}`;
  logger.log(`[${params.provider} Route] params `, params);
  switch (apiPath) {
    case ApiPath.Azure:
      return azureHandler(req, { params });
    case ApiPath.Google:
      return googleHandler(req, { params });
    case ApiPath.Anthropic:
      return anthropicHandler(req, { params });
    case ApiPath.Baidu:
      return baiduHandler(req, { params });
    case ApiPath.ByteDance:
      return bytedanceHandler(req, { params });
    case ApiPath.Alibaba:
      return alibabaHandler(req, { params });
    // case ApiPath.Tencent: using "/api/tencent"
    case ApiPath.Moonshot:
      return moonshotHandler(req, { params });
    case ApiPath.Stability:
      return stabilityHandler(req, { params });
    case ApiPath.Iflytek:
      return iflytekHandler(req, { params });
    case ApiPath.DeepSeek:
      return deepseekHandler(req, { params });
    case ApiPath.XAI:
      return xaiHandler(req, { params });
    case ApiPath.ChatGLM:
      return chatglmHandler(req, { params });
    case ApiPath.SiliconFlow:
      return siliconflowHandler(req, { params });
    case "/api/openai": // OpenAI removed, using hardcoded path
      // OpenAI is disabled, redirect to Alibaba
      return new Response(
        JSON.stringify({
          error: "OpenAI API is disabled. Please use Alibaba provider instead.",
          code: "OPENAI_DISABLED",
        }),
        {
          status: 403,
          headers: { "Content-Type": "application/json" },
        },
      );
    default:
      return proxyHandler(req, { params });
  }
}

export const GET = handle;
export const POST = handle;

export const runtime = "edge";
export const preferredRegion = [
  "arn1",
  "bom1",
  "cdg1",
  "cle1",
  "cpt1",
  "dub1",
  "fra1",
  "gru1",
  "hnd1",
  "iad1",
  "icn1",
  "kix1",
  "lhr1",
  "pdx1",
  "sfo1",
  "sin1",
  "syd1",
];
