import {
  getMessageTextContent,
  isDalle3,
  safeLocalStorage,
  trimTopic,
} from "../utils";
import { logger } from "../utils/logger";

import { indexedDBStorage } from "@/app/utils/indexedDB-storage";
import { nanoid } from "nanoid";
import type { ClientApi, RequestMessage } from "../client/api";
import { getClientApi } from "../client/api";
import { showToast } from "../components/ui-lib";
import {
  DEFAULT_INPUT_TEMPLATE,
  DEFAULT_MODELS,
  DEFAULT_SYSTEM_TEMPLATE,
  GEMINI_SUMMARIZE_MODEL,
  DEEPSEEK_SUMMARIZE_MODEL,
  KnowledgeCutOffDate,
  MCP_SYSTEM_TEMPLATE,
  MCP_TOOLS_TEMPLATE,
  ServiceProvider,
  StoreKey,
  SUMMARIZE_MODEL,
} from "../constant";
import Locale, { getLang } from "../locales";
import { createPersistStore } from "../utils/store";
import { estimateTokenLength } from "../utils/token";
import { ModelConfig, ModelType, useAppConfig } from "./config";
import { useAccessStore } from "./access";
import { collectModelsWithDefaultModel } from "../utils/model";
import { createEmptyMask, Mask } from "./mask";
import { executeMcpAction, getAllTools, isMcpEnabled } from "../mcp/actions";
import { extractMcpJson, isMcpJson } from "../mcp/utils";

const localStorage = safeLocalStorage();

export type ChatMessageTool = {
  id: string;
  index?: number;
  type?: string;
  function?: {
    name: string;
    arguments?: string;
  };
  content?: string;
  isError?: boolean;
  errorMsg?: string;
};

export type ChatMessage = RequestMessage & {
  date: string;
  streaming?: boolean;
  isError?: boolean;
  id: string;
  model?: ModelType;
  tools?: ChatMessageTool[];
  audio_url?: string;
  isMcpResponse?: boolean;
  loadingStage?: "connecting" | "processing" | "generating" | "error";
};

export function createMessage(override: Partial<ChatMessage>): ChatMessage {
  return {
    id: nanoid(),
    date: new Date().toLocaleString(),
    role: "user",
    content: "",
    ...override,
  };
}

export interface ChatStat {
  tokenCount: number;
  wordCount: number;
  charCount: number;
}

export interface ChatSession {
  id: string;
  topic: string;

  memoryPrompt: string;
  messages: ChatMessage[];
  stat: ChatStat;
  lastUpdate: number;
  lastSummarizeIndex: number;
  clearContextIndex?: number;

  mask: Mask;
}

export const DEFAULT_TOPIC = Locale.Store.DefaultTopic;
export const BOT_HELLO: ChatMessage = createMessage({
  role: "assistant",
  content: Locale.Store.BotHello,
});

function createEmptySession(): ChatSession {
  return {
    id: nanoid(),
    topic: DEFAULT_TOPIC,
    memoryPrompt: "",
    messages: [],
    stat: {
      tokenCount: 0,
      wordCount: 0,
      charCount: 0,
    },
    lastUpdate: Date.now(),
    lastSummarizeIndex: 0,

    mask: createEmptyMask(),
  };
}

function getSummarizeModel(
  currentModel: string,
  providerName: string,
): string[] {
  // if it is using gpt-* models, force to use 4o-mini to summarize
  if (currentModel.startsWith("gpt") || currentModel.startsWith("chatgpt")) {
    const configStore = useAppConfig.getState();
    const accessStore = useAccessStore.getState();
    const allModel = collectModelsWithDefaultModel(
      configStore.models,
      [configStore.customModels, accessStore.customModels].join(","),
      accessStore.defaultModel,
    );
    const summarizeModel = allModel.find(
      (m) => m.name === SUMMARIZE_MODEL && m.available,
    );
    if (summarizeModel) {
      return [
        summarizeModel.name,
        summarizeModel.provider?.providerName as string,
      ];
    }
  }
  if (currentModel.startsWith("gemini")) {
    return [GEMINI_SUMMARIZE_MODEL, ServiceProvider.Google];
  } else if (currentModel.startsWith("deepseek-")) {
    return [DEEPSEEK_SUMMARIZE_MODEL, ServiceProvider.DeepSeek];
  }

  return [currentModel, providerName];
}

function countMessages(msgs: ChatMessage[]) {
  return msgs.reduce(
    (pre, cur) => pre + estimateTokenLength(getMessageTextContent(cur)),
    0,
  );
}

function fillTemplateWith(input: string, modelConfig: ModelConfig) {
  const cutoff =
    KnowledgeCutOffDate[modelConfig.model] ?? KnowledgeCutOffDate.default;
  // Find the model in the DEFAULT_MODELS array that matches the modelConfig.model
  const modelInfo = DEFAULT_MODELS.find((m) => m.name === modelConfig.model);

  var serviceProvider = "Alibaba";
  if (modelInfo) {
    // TODO: auto detect the providerName from the modelConfig.model

    // Directly use the providerName from the modelInfo
    serviceProvider = modelInfo.provider.providerName;
  }

  const vars = {
    ServiceProvider: serviceProvider,
    cutoff,
    model: modelConfig.model,
    time: new Date().toString(),
    lang: getLang(),
    input: input,
  };

  let output = modelConfig.template ?? DEFAULT_INPUT_TEMPLATE;

  // remove duplicate
  if (input.startsWith(output)) {
    output = "";
  }

  // must contains {{input}}
  const inputVar = "{{input}}";
  if (!output.includes(inputVar)) {
    output += "\n" + inputVar;
  }

  Object.entries(vars).forEach(([name, value]) => {
    const regex = new RegExp(`{{${name}}}`, "g");
    output = output.replace(regex, value.toString()); // Ensure value is a string
  });

  return output;
}

async function getMcpSystemPrompt(): Promise<string> {
  const tools = await getAllTools();

  let toolsStr = "";

  tools.forEach((i) => {
    // error client has no tools
    if (!i.tools) return;

    toolsStr += MCP_TOOLS_TEMPLATE.replace(
      "{{ clientId }}",
      i.clientId,
    ).replace(
      "{{ tools }}",
      i.tools.tools.map((p: object) => JSON.stringify(p, null, 2)).join("\n"),
    );
  });

  return MCP_SYSTEM_TEMPLATE.replace("{{ MCP_TOOLS }}", toolsStr);
}

const DEFAULT_CHAT_STATE = {
  sessions: [createEmptySession()],
  currentSessionIndex: 0,
  lastInput: "",
};

export const useChatStore = createPersistStore(
  DEFAULT_CHAT_STATE,
  (set, _get) => {
    function get() {
      return {
        ..._get(),
        ...methods,
      };
    }

    const methods = {
      getPersistentUserId() {
        // 从localStorage获取或生成持久化用户ID
        const PERSISTENT_USER_ID_KEY = "persistent_user_id";
        let userId = localStorage.getItem(PERSISTENT_USER_ID_KEY);

        if (!userId) {
          // 生成新的用户ID
          userId = "user_" + nanoid();
          localStorage.setItem(PERSISTENT_USER_ID_KEY, userId);
          logger.info("Generated new persistent user ID:", userId);
        }

        return userId;
      },

      forkSession() {
        // 获取当前会话
        const currentSession = get().currentSession();
        if (!currentSession) return;

        const newSession = createEmptySession();

        newSession.topic = currentSession.topic;
        // 深拷贝消息
        newSession.messages = currentSession.messages.map((msg) => ({
          ...msg,
          id: nanoid(), // 生成新的消息 ID
        }));
        newSession.mask = {
          ...currentSession.mask,
          modelConfig: {
            ...currentSession.mask.modelConfig,
          },
        };

        set((state) => ({
          currentSessionIndex: 0,
          sessions: [newSession, ...state.sessions],
        }));
      },

      clearSessions() {
        set(() => ({
          sessions: [createEmptySession()],
          currentSessionIndex: 0,
        }));
      },

      selectSession(index: number) {
        set({
          currentSessionIndex: index,
        });
      },

      moveSession(from: number, to: number) {
        set((state) => {
          const { sessions, currentSessionIndex: oldIndex } = state;

          // move the session
          const newSessions = [...sessions];
          const session = newSessions[from];
          newSessions.splice(from, 1);
          newSessions.splice(to, 0, session);

          // modify current session id
          let newIndex = oldIndex === from ? to : oldIndex;
          if (oldIndex > from && oldIndex <= to) {
            newIndex -= 1;
          } else if (oldIndex < from && oldIndex >= to) {
            newIndex += 1;
          }

          return {
            currentSessionIndex: newIndex,
            sessions: newSessions,
          };
        });
      },

      newSession(mask?: Mask) {
        const session = createEmptySession();

        if (mask) {
          const config = useAppConfig.getState();
          const globalModelConfig = config.modelConfig;

          session.mask = {
            ...mask,
            modelConfig: {
              ...globalModelConfig,
              ...mask.modelConfig,
            },
          };
          session.topic = mask.name;
        }

        set((state) => ({
          currentSessionIndex: 0,
          sessions: [session].concat(state.sessions),
        }));
      },

      nextSession(delta: number) {
        const n = get().sessions.length;
        const limit = (x: number) => (x + n) % n;
        const i = get().currentSessionIndex;
        get().selectSession(limit(i + delta));
      },

      deleteSession(index: number) {
        const deletingLastSession = get().sessions.length === 1;
        const deletedSession = get().sessions.at(index);

        if (!deletedSession) return;

        // 如果是Agent会话，先调用后端删除API
        const agentSessionId = (deletedSession as any).agentSessionId;
        if (agentSessionId) {
          // 获取后端 API 基础 URL
          const apiBaseUrl =
            process.env.NEXT_PUBLIC_API_BASE_URL || "https://www.ifish.me";

          // 异步调用后端删除API，不阻塞前端操作
          fetch(`${apiBaseUrl}/flask/agent/remove/${agentSessionId}`, {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
            },
          })
            .then((response) => {
              if (response.ok) {
                logger.info(`成功删除后端Agent会话: ${agentSessionId}`);
              } else {
                logger.warn(
                  `删除后端Agent会话失败: ${agentSessionId}, 状态码: ${response.status}`,
                );
              }
            })
            .catch((error) => {
              logger.warn(`删除后端Agent会话异常: ${agentSessionId}`, error);
            });

          // 清除前端存储的agentSessionId，避免重新创建会话时使用无效的session_id
          (deletedSession as any).agentSessionId = undefined;
        }

        const sessions = get().sessions.slice();
        sessions.splice(index, 1);

        const currentIndex = get().currentSessionIndex;
        let nextIndex = Math.min(
          currentIndex - Number(index < currentIndex),
          sessions.length - 1,
        );

        if (deletingLastSession) {
          nextIndex = 0;
          sessions.push(createEmptySession());
        }

        // for undo delete action
        const restoreState = {
          currentSessionIndex: get().currentSessionIndex,
          sessions: get().sessions.slice(),
        };

        set(() => ({
          currentSessionIndex: nextIndex,
          sessions,
        }));

        showToast(
          Locale.Home.DeleteToast,
          {
            text: Locale.Home.Revert,
            onClick() {
              set(() => restoreState);
              // 如果撤销删除，需要重新创建Agent会话
              if (agentSessionId) {
                logger.info(
                  `撤销删除会话，Agent会话ID: ${agentSessionId} 将在下次对话时重新创建`,
                );
              }
            },
          },
          5000,
        );
      },

      currentSession() {
        let index = get().currentSessionIndex;
        const sessions = get().sessions;

        if (index < 0 || index >= sessions.length) {
          index = Math.min(sessions.length - 1, Math.max(0, index));
          set(() => ({ currentSessionIndex: index }));
        }

        const session = sessions[index];

        return session;
      },

      onNewMessage(message: ChatMessage, targetSession: ChatSession) {
        get().updateTargetSession(targetSession, (session) => {
          session.messages = session.messages.concat();
          session.lastUpdate = Date.now();
        });

        get().updateStat(message, targetSession);

        get().checkMcpJson(message);

        get().summarizeSession(false, targetSession);
      },

      async onUserInput(
        content: string,
        attachImages?: string[],
        isMcpResponse?: boolean,
      ) {
        const session = get().currentSession();

        // Debug: 打印当前会话配置
        logger.debug("Current session mask:", session.mask);

        // Check if this session has specific agent configuration
        const agentType = (session.mask as any).agentType;
        const maskId = session.mask.id;

        // Use Agent API for all requests
        // If no specific agent type, use default general agent
        const finalAgentType = agentType || "general";

        logger.info(
          `[Agent聊天请求] 用户输入: "${content}", Agent类型: ${finalAgentType}`,
        );

        return await get().callAgentAPI(
          content,
          attachImages,
          finalAgentType,
          maskId,
        );
      },

      async callAgentAPI(
        content: string,
        attachImages?: string[],
        agentType?: string,
        maskId?: string,
        isRetry: boolean = false,
      ): Promise<void> {
        const session = get().currentSession();
        // 生成或获取持久化用户ID
        const userId = get().getPersistentUserId();
        const { RetryManager, RetryPresets } = await import(
          "../utils/retry-manager"
        );

        // Create user message (only if not a retry)
        let userMessage: ChatMessage;
        let botMessage: ChatMessage;

        if (!isRetry) {
          userMessage = createMessage({
            role: "user",
            content: content,
          });

          // Create bot message
          botMessage = createMessage({
            role: "assistant",
            streaming: true,
            model: agentType || "agent",
            loadingStage: "connecting", // 初始加载阶段
          });

          // Save messages to session
          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat([
              userMessage,
              botMessage,
            ]);
          });
        } else {
          // 重试时，获取最后的用户消息和机器人消息
          const messages = session.messages;

          // 安全检查：确保有足够的消息
          if (messages.length < 2) {
            throw new Error("消息历史不足，无法重试");
          }

          userMessage = messages[messages.length - 2]; // 倒数第二条是用户消息
          botMessage = messages[messages.length - 1]; // 最后一条是机器人消息

          // 安全检查：确保获取到的是正确的消息类型
          if (!userMessage || userMessage.role !== "user") {
            throw new Error("无法找到用户消息，请重新发送");
          }

          if (!botMessage || botMessage.role !== "assistant") {
            throw new Error("无法找到机器人消息，请重新发送");
          }

          // 重置机器人消息状态
          botMessage.streaming = true;
          botMessage.isError = false;
          botMessage.content = "正在重新连接...";
          botMessage.loadingStage = "connecting";

          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
          });
        }

        // 使用重试机制包装API调用
        const retryResult = await RetryManager.smartRetry(
          async () => {
            return await get().performAgentAPICall(
              content,
              attachImages,
              agentType,
              maskId,
              session,
              botMessage,
              userMessage,
              userId,
              isRetry,
            );
          },
          {
            ...RetryPresets.network,
            onRetry: (attempt, error) => {
              console.log(`重试第 ${attempt} 次:`, error.message);
              botMessage.loadingStage = "connecting";
              botMessage.content = `网络连接不稳定，正在重试 (${attempt}/${RetryPresets.network.maxRetries})...`;
              get().updateTargetSession(session, (session) => {
                session.messages = session.messages.concat();
              });
            },
          },
        );

        if (!retryResult.success) {
          // 所有重试都失败了
          get().handleFinalError(
            retryResult.error,
            botMessage,
            userMessage,
            session,
            isRetry,
          );
        }
      },

      // 执行实际的API调用
      async performAgentAPICall(
        content: string,
        attachImages: string[] | undefined,
        agentType: string | undefined,
        maskId: string | undefined,
        session: ChatSession,
        botMessage: ChatMessage,
        userMessage: ChatMessage,
        userId: string,
        isRetry: boolean,
      ): Promise<void> {
        const { ChatControllerPool } = await import("../client/controller");

        // 创建AbortController来支持取消功能
        const controller = new AbortController();
        const messageId = botMessage.id || "";

        // 将controller添加到池中
        ChatControllerPool.addController(session.id, messageId, controller);

        try {
          // 更新加载状态为处理中
          botMessage.loadingStage = "processing";
          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
          });
          // 获取后端 API 基础 URL（使用客户端环境变量）
          const apiBaseUrl =
            process.env.NEXT_PUBLIC_API_BASE_URL || "https://www.ifish.me";

          // 检查现有的agent session是否有效
          let sessionId = (session as any).agentSessionId;
          let needsInit = !sessionId;

          // 如果有sessionId，先验证它是否仍然有效（仅在非重试时进行验证）
          if (sessionId && !isRetry) {
            try {
              // 使用AbortController来实现超时控制
              const controller = new AbortController();
              const timeoutId = setTimeout(() => controller.abort(), 5000);

              const testResponse = await fetch(
                `${apiBaseUrl}/flask/agent/session/${sessionId}/status`,
                {
                  method: "GET",
                  signal: controller.signal,
                },
              );

              clearTimeout(timeoutId);

              if (!testResponse.ok || testResponse.status === 404) {
                logger.warn(
                  "Agent API Session validation failed, session not found or expired",
                );
                needsInit = true;
                sessionId = null;
                (session as any).agentSessionId = null;
              } else {
                const statusData = await testResponse.json();
                if (!statusData.success || !statusData.exists) {
                  logger.warn(
                    "Agent API Session validation failed, session invalid",
                  );
                  needsInit = true;
                  sessionId = null;
                  (session as any).agentSessionId = null;
                }
              }
            } catch (error) {
              logger.warn(
                "Agent API Session validation failed, will reinitialize",
                error,
              );
              needsInit = true;
              sessionId = null;
              (session as any).agentSessionId = null;
            }
          }

          // Initialize agent session if needed
          if (needsInit) {
            let initResponse;

            // 如果有旧的sessionId，先尝试恢复会话
            if ((session as any).agentSessionId && !isRetry) {
              try {
                const recoverResponse = await fetch(
                  `${apiBaseUrl}/flask/agent/recover`,
                  {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                    },
                    signal: controller.signal,
                    body: JSON.stringify({
                      user_id: userId,
                      mask_id: maskId || "default",
                      agent_type: agentType || "ticket",
                      session_id: (session as any).agentSessionId,
                      session_uuid: session.mask.sessionUuid,
                    }),
                  },
                );

                if (recoverResponse.ok) {
                  const recoverData = await recoverResponse.json();
                  if (recoverData.success) {
                    sessionId = recoverData.session_id;
                    (session as any).agentSessionId = sessionId;
                    logger.info(
                      `Agent API Session recovery ${recoverData.recovered ? "successful" : "created new"}: ${sessionId}`,
                    );
                    needsInit = false;
                  }
                }
              } catch (error) {
                logger.warn(
                  "Agent API Session recovery failed, will create new session",
                  error,
                );
              }
            }

            // 如果恢复失败，创建新会话
            if (needsInit) {
              // 获取sessionUuid（如果存在）
              const sessionUuid = session.mask.sessionUuid;

              initResponse = await fetch(`${apiBaseUrl}/flask/agent/init`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                signal: controller.signal,
                body: JSON.stringify({
                  user_id: userId,
                  mask_id: maskId || "default",
                  agent_type: agentType || "ticket",
                  session_uuid: sessionUuid, // 传递sessionUuid
                  force_new: !!sessionUuid, // 如果有sessionUuid，强制创建新会话
                }),
              });

              if (!initResponse.ok) {
                throw new Error("初始化Agent会话失败，请稍后重试");
              }

              const initData = await initResponse.json();
              sessionId = initData.session_id;
              (session as any).agentSessionId = sessionId;
            }
          }

          // Send message to agent with streaming support
          const chatResponse = await fetch(`${apiBaseUrl}/flask/agent/chat`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            signal: controller.signal,
            body: JSON.stringify({
              session_id: sessionId,
              message: content,
              file_paths: attachImages || [],
            }),
          });

          // 打印用户输入的问题和对应的agent信息
          logger.info(
            `[聊天请求] 用户输入: "${content}", Agent类型: ${agentType || "ticket"}, 会话ID: ${sessionId}`,
          );

          logger.info(
            `Agent API Sending chat request with session_id: ${sessionId}`,
          );

          if (!chatResponse.ok) {
            // 如果chat请求失败，可能是session过期
            if (chatResponse.status === 404) {
              logger.warn("Agent API Session not found, clearing sessionId");
              (session as any).agentSessionId = null;

              // 如果不是重试，则自动重试一次
              if (!isRetry) {
                logger.info("Agent API Attempting auto-retry...");
                return await get().callAgentAPI(
                  content,
                  attachImages,
                  agentType,
                  maskId,
                  true,
                );
              } else {
                throw new Error("会话已过期，请重新发送消息");
              }
            }

            // 其他错误
            const errorMsg =
              chatResponse.status === 500
                ? "服务器内部错误，请稍后重试"
                : `连接失败 (${chatResponse.status})，请检查网络连接`;
            throw new Error(errorMsg);
          }

          // 更新加载状态为生成中
          botMessage.loadingStage = "generating";
          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
          });

          // 处理流式响应
          await get().handleStreamingResponse(
            chatResponse,
            botMessage,
            session,
            sessionId,
          );
        } catch (error) {
          // 重新抛出错误，让重试机制处理
          throw error;
        } finally {
          // 清理controller（但不要在这里清理，因为simulateTypingEffect还需要使用）
          // ChatControllerPool.remove(session.id, messageId);
        }
      },

      // 处理最终错误（所有重试都失败后）
      handleFinalError(
        error: any,
        botMessage: ChatMessage,
        userMessage: ChatMessage,
        session: ChatSession,
        isRetry: boolean,
      ): void {
        // 打印错误信息
        logger.error("[聊天最终错误]", error);

        // Update bot message with error
        botMessage.streaming = false;
        botMessage.loadingStage = "error";

        // 提供更友好的错误信息和操作建议
        let errorMessage = "";

        if (error instanceof Error) {
          if (error.message.includes("会话已过期")) {
            errorMessage = "会话已过期，请点击重试按钮重新发送消息";
          } else if (error.message.includes("服务器内部错误")) {
            errorMessage = "服务器暂时繁忙，已尝试多次重试，请稍后再试";
          } else if (error.message.includes("连接失败")) {
            errorMessage = "网络连接异常，已尝试多次重试，请检查网络后重试";
          } else if (error.message.includes("初始化Agent会话失败")) {
            errorMessage = "Agent服务初始化失败，已尝试多次重试，请稍后重试";
          } else if (
            error.name === "AbortError" ||
            error.message.includes("aborted") ||
            error.message.includes("The user aborted a request")
          ) {
            // 处理网络请求被中止的情况（通常是网络超时或连接问题）
            errorMessage = "网络连接失败，请联系管理员";
          } else if (
            error.message.includes("timeout") ||
            error.message.includes("超时")
          ) {
            errorMessage = "网络连接失败，请联系管理员";
          } else if (
            error.message.includes("fetch") ||
            error.message.includes("network") ||
            error.message.includes("Failed to fetch")
          ) {
            errorMessage = "网络连接失败，请联系管理员";
          } else {
            errorMessage = `${error.message}（已尝试多次重试）`;
          }
        } else {
          errorMessage = "网络连接失败，请联系管理员";
        }

        botMessage.content = errorMessage;
        botMessage.isError = true;

        // 确保userMessage存在时才设置错误状态
        if (userMessage) {
          userMessage.isError = true;
        }

        get().updateTargetSession(session, (session) => {
          session.messages = session.messages.concat();
        });
      },

      // 处理流式响应
      async handleStreamingResponse(
        response: Response,
        botMessage: ChatMessage,
        session: ChatSession,
        sessionId: string,
      ): Promise<void> {
        const { ChatControllerPool } = await import("../client/controller");
        const messageId = botMessage.id || "";

        // 获取已存在的controller
        const key = ChatControllerPool.key(session.id, messageId);
        let controller = ChatControllerPool.controllers[key];

        if (!controller) {
          console.warn("No controller found for message, creating new one");
          controller = new AbortController();
          ChatControllerPool.addController(session.id, messageId, controller);
        }

        // 设置初始状态
        botMessage.streaming = true;
        botMessage.content = "";
        botMessage.isError = false;
        botMessage.loadingStage = "generating";

        // 更新会话以显示空的机器人消息
        get().updateTargetSession(session, (session) => {
          session.messages = session.messages.concat();
        });

        try {
          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("无法获取响应流");
          }

          const decoder = new TextDecoder();
          let buffer = "";
          let fullResponse = "";

          while (true) {
            if (controller.signal.aborted) {
              // 用户取消，关闭reader并退出循环
              try {
                await reader.cancel();
              } catch (e) {
                console.warn("关闭reader失败:", e);
              }
              break;
            }

            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));

                  // 打印每次接收到的流式响应数据
                  logger.log(
                    `[Agent流式响应] 接收数据类型: ${data.type}, 内容: ${data.content ? `"${data.content.substring(0, 100)}${data.content.length > 100 ? "..." : ""}"` : "无内容"}, 会话ID: ${sessionId}`,
                  );

                  if (data.type === "chunk" && data.content) {
                    fullResponse += data.content;
                    botMessage.content = fullResponse;

                    // 实时更新UI
                    get().updateTargetSession(session, (session) => {
                      session.messages = session.messages.concat();
                    });
                  } else if (data.type === "complete") {
                    // 流式响应完成
                    logger.info(
                      `[聊天响应] Agent流式回复完成: "${fullResponse || "Agent暂无回复"}", 会话ID: ${sessionId}`,
                    );
                    break;
                  } else if (data.type === "error") {
                    throw new Error(data.error || "流式响应出错");
                  } else if (data.type === "done") {
                    // 后端发送的结束标记
                    logger.log(
                      `[Agent流式响应] 接收到结束标记, 会话ID: ${sessionId}`,
                    );
                    break;
                  }
                } catch (parseError) {
                  console.warn("解析流式数据失败:", line, parseError);
                }
              }
            }
          }

          // 完成显示，设置最终状态
          botMessage.streaming = false;
          botMessage.content = fullResponse || "Agent暂无回复";
          botMessage.date = new Date().toLocaleString();
          botMessage.isError = false;
          botMessage.loadingStage = undefined;

          // 一次性更新所有状态，避免多次触发UI更新
          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
            session.lastUpdate = Date.now();
            // 直接在这里更新统计信息，避免额外的updateTargetSession调用
            session.stat.charCount += botMessage.content.length;
          });

          // 检查MCP JSON和会话摘要（这些不会触发额外的UI更新）
          get().checkMcpJson(botMessage);
          get().summarizeSession(false, session);
        } catch (error) {
          console.error("流式响应处理错误:", error);

          // 检查是否是用户主动取消
          if (controller.signal.aborted) {
            // 用户主动取消，保留已打印的内容并停止流式状态
            botMessage.streaming = false;
            botMessage.date = new Date().toLocaleString();
            botMessage.isError = false;
            botMessage.loadingStage = undefined;
            // 不修改content，保留已经打印的内容
          } else {
            // 其他错误，显示错误信息
            botMessage.streaming = false;
            botMessage.content = `流式响应出错: ${error instanceof Error ? error.message : "未知错误"}`;
            botMessage.date = new Date().toLocaleString();
            botMessage.isError = true;
            botMessage.loadingStage = "error";
          }

          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
          });

          // 如果不是用户主动取消，重新抛出错误让重试机制处理
          if (!controller.signal.aborted) {
            throw error;
          }
        } finally {
          // 清理controller
          ChatControllerPool.remove(session.id, messageId);
        }
      },

      // 模拟打字机效果的流式显示
      async simulateTypingEffect(
        botMessage: ChatMessage,
        fullResponse: string,
        session: ChatSession,
      ): Promise<void> {
        const { ChatControllerPool } = await import("../client/controller");
        const { createTypingEffect } = await import("../utils/typing-effect");

        const messageId = botMessage.id || "";

        // 获取已存在的controller（由performAgentAPICall创建）
        const key = ChatControllerPool.key(session.id, messageId);
        let controller = ChatControllerPool.controllers[key];

        if (!controller) {
          console.warn("No controller found for message, creating new one");
          controller = new AbortController();
          ChatControllerPool.addController(session.id, messageId, controller);
        }

        // 设置初始状态
        botMessage.streaming = true;
        botMessage.content = "";
        botMessage.isError = false;
        botMessage.loadingStage = "generating"; // 新增加载阶段

        // 更新会话以显示空的机器人消息
        get().updateTargetSession(session, (session) => {
          session.messages = session.messages.concat();
        });

        try {
          // 创建打字机效果实例
          const typingEffect = createTypingEffect({
            baseSpeed: 40, // 稍微提高基础速度
            adaptiveSpeed: true,
            maxLength: 50000,
            maxRetries: 3,
            enableMemoryMonitor: true,
          });

          // 开始打字机效果
          await typingEffect.start(fullResponse, {
            onUpdate: (content: string) => {
              // 更新消息内容
              botMessage.content = content;
              botMessage.loadingStage = "generating";

              // 更新会话
              get().updateTargetSession(session, (session) => {
                session.messages = session.messages.concat();
              });
            },
            onComplete: (content: string) => {
              // 完成显示，设置最终状态
              botMessage.streaming = false;
              botMessage.content = content;
              botMessage.date = new Date().toLocaleString();
              botMessage.isError = false;
              botMessage.loadingStage = undefined;

              get().updateTargetSession(session, (session) => {
                session.messages = session.messages.concat();
              });

              get().onNewMessage(botMessage, session);
            },
            onError: (error: Error) => {
              console.error("打字机效果执行错误:", error);

              // 检查是否是用户主动取消
              if (controller?.signal.aborted) {
                // 用户主动取消，保留已打印的内容并停止流式状态
                botMessage.streaming = false;
                botMessage.date = new Date().toLocaleString();
                botMessage.isError = false;
                botMessage.loadingStage = undefined;
                // 不修改content，保留已经打印的内容
              } else {
                // 其他错误，显示完整内容并标记错误
                botMessage.streaming = false;
                botMessage.content = fullResponse;
                botMessage.date = new Date().toLocaleString();
                botMessage.isError = true;
                botMessage.loadingStage = "error";
              }

              get().updateTargetSession(session, (session) => {
                session.messages = session.messages.concat();
              });

              get().onNewMessage(botMessage, session);
            },
            shouldAbort: () => {
              // 检查是否被中止或用户切换了会话
              if (controller?.signal.aborted) {
                return true;
              }

              const currentSession = get().currentSession();
              return currentSession.id !== session.id;
            },
          });
        } catch (error) {
          console.error("打字机效果初始化错误:", error);

          // 检查是否是用户主动取消
          if (controller?.signal.aborted) {
            // 用户主动取消，保留已打印的内容并停止流式状态
            botMessage.streaming = false;
            botMessage.date = new Date().toLocaleString();
            botMessage.isError = false;
            botMessage.loadingStage = undefined;
            // 不修改content，保留已经打印的内容
          } else {
            // 其他错误，直接显示完整内容
            botMessage.streaming = false;
            botMessage.content = fullResponse;
            botMessage.date = new Date().toLocaleString();
            botMessage.isError = true;
            botMessage.loadingStage = "error";
          }

          get().updateTargetSession(session, (session) => {
            session.messages = session.messages.concat();
          });

          get().onNewMessage(botMessage, session);
        } finally {
          // 清理controller
          ChatControllerPool.remove(session.id, messageId);
        }
      },

      getMemoryPrompt() {
        const session = get().currentSession();

        if (session.memoryPrompt.length) {
          return {
            role: "system",
            content: Locale.Store.Prompt.History(session.memoryPrompt),
            date: "",
          } as ChatMessage;
        }
      },

      async getMessagesWithMemory() {
        const session = get().currentSession();
        const modelConfig = session.mask.modelConfig;
        const clearContextIndex = session.clearContextIndex ?? 0;
        const messages = session.messages.slice();
        const totalMessageCount = session.messages.length;

        // in-context prompts
        const contextPrompts = session.mask.context.slice();

        // system prompts, to get close to OpenAI Web ChatGPT
        // 修改为支持所有模型的系统提示词注入，不仅限于 GPT 模型
        const shouldInjectSystemPrompts = modelConfig.enableInjectSystemPrompts;

        const mcpEnabled = await isMcpEnabled();
        const mcpSystemPrompt = mcpEnabled ? await getMcpSystemPrompt() : "";

        var systemPrompts: ChatMessage[] = [];

        if (shouldInjectSystemPrompts) {
          systemPrompts = [
            createMessage({
              role: "system",
              content:
                fillTemplateWith("", {
                  ...modelConfig,
                  template: DEFAULT_SYSTEM_TEMPLATE,
                }) + mcpSystemPrompt,
            }),
          ];
        } else if (mcpEnabled) {
          systemPrompts = [
            createMessage({
              role: "system",
              content: mcpSystemPrompt,
            }),
          ];
        }

        if (shouldInjectSystemPrompts || mcpEnabled) {
          logger.debug(
            "Global System Prompt:",
            systemPrompts.at(0)?.content ?? "empty",
          );
        }
        const memoryPrompt = get().getMemoryPrompt();
        // long term memory
        const shouldSendLongTermMemory =
          modelConfig.sendMemory &&
          session.memoryPrompt &&
          session.memoryPrompt.length > 0 &&
          session.lastSummarizeIndex > clearContextIndex;
        const longTermMemoryPrompts =
          shouldSendLongTermMemory && memoryPrompt ? [memoryPrompt] : [];
        const longTermMemoryStartIndex = session.lastSummarizeIndex;

        // short term memory
        const shortTermMemoryStartIndex = Math.max(
          0,
          totalMessageCount - modelConfig.historyMessageCount,
        );

        // lets concat send messages, including 4 parts:
        // 0. system prompt: to get close to OpenAI Web ChatGPT
        // 1. long term memory: summarized memory messages
        // 2. pre-defined in-context prompts
        // 3. short term memory: latest n messages
        // 4. newest input message
        const memoryStartIndex = shouldSendLongTermMemory
          ? Math.min(longTermMemoryStartIndex, shortTermMemoryStartIndex)
          : shortTermMemoryStartIndex;
        // and if user has cleared history messages, we should exclude the memory too.
        const contextStartIndex = Math.max(clearContextIndex, memoryStartIndex);
        const maxTokenThreshold = modelConfig.max_tokens;

        // get recent messages as much as possible
        const reversedRecentMessages = [];
        for (
          let i = totalMessageCount - 1, tokenCount = 0;
          i >= contextStartIndex && tokenCount < maxTokenThreshold;
          i -= 1
        ) {
          const msg = messages[i];
          if (!msg || msg.isError) continue;
          tokenCount += estimateTokenLength(getMessageTextContent(msg));
          reversedRecentMessages.push(msg);
        }
        // concat all messages
        const recentMessages = [
          ...systemPrompts,
          ...longTermMemoryPrompts,
          ...contextPrompts,
          ...reversedRecentMessages.reverse(),
        ];

        return recentMessages;
      },

      updateMessage(
        sessionIndex: number,
        messageIndex: number,
        updater: (message?: ChatMessage) => void,
      ) {
        const sessions = get().sessions;
        const session = sessions.at(sessionIndex);
        const messages = session?.messages;
        updater(messages?.at(messageIndex));
        set(() => ({ sessions }));
      },

      resetSession(session: ChatSession) {
        get().updateTargetSession(session, (session) => {
          session.messages = [];
          session.memoryPrompt = "";
        });
      },

      summarizeSession(
        refreshTitle: boolean = false,
        targetSession: ChatSession,
      ) {
        const config = useAppConfig.getState();
        const session = targetSession;
        const modelConfig = session.mask.modelConfig;
        // 如果使用dalle3模型则跳过总结
        if (isDalle3(modelConfig.model)) {
          return;
        }

        // 如果没有配置压缩模型，则使用getSummarizeModel获取
        const [model, providerName] = modelConfig.compressModel
          ? [modelConfig.compressModel, modelConfig.compressProviderName]
          : getSummarizeModel(
              session.mask.modelConfig.model,
              session.mask.modelConfig.providerName,
            );
        const api: ClientApi = getClientApi(providerName as ServiceProvider);

        // 移除错误消息
        const messages = session.messages;

        // 当聊天内容超过50个字符时才进行主题总结
        const SUMMARIZE_MIN_LEN = 50;
        if (
          (config.enableAutoGenerateTitle &&
            session.topic === DEFAULT_TOPIC &&
            countMessages(messages) >= SUMMARIZE_MIN_LEN) ||
          refreshTitle
        ) {
          const startIndex = Math.max(
            0,
            messages.length - modelConfig.historyMessageCount,
          );
          const topicMessages = messages
            .slice(
              startIndex < messages.length ? startIndex : messages.length - 1,
              messages.length,
            )
            .concat(
              createMessage({
                role: "user",
                content: Locale.Store.Prompt.Topic,
              }),
            );
          api.llm.chat({
            messages: topicMessages,
            config: {
              model,
              stream: false,
              providerName,
            },
            onFinish(message, responseRes) {
              if (responseRes?.status === 200) {
                get().updateTargetSession(
                  session,
                  (session) =>
                    (session.topic =
                      message.length > 0 ? trimTopic(message) : DEFAULT_TOPIC),
                );
              }
            },
          });
        }
        const summarizeIndex = Math.max(
          session.lastSummarizeIndex,
          session.clearContextIndex ?? 0,
        );
        let toBeSummarizedMsgs = messages
          .filter((msg) => !msg.isError)
          .slice(summarizeIndex);

        const historyMsgLength = countMessages(toBeSummarizedMsgs);

        if (historyMsgLength > (modelConfig?.max_tokens || 4000)) {
          const n = toBeSummarizedMsgs.length;
          toBeSummarizedMsgs = toBeSummarizedMsgs.slice(
            Math.max(0, n - modelConfig.historyMessageCount),
          );
        }
        const memoryPrompt = get().getMemoryPrompt();
        if (memoryPrompt) {
          // 添加记忆提示
          toBeSummarizedMsgs.unshift(memoryPrompt);
        }

        const lastSummarizeIndex = session.messages.length;

        logger.debug(
          "Chat History:",
          toBeSummarizedMsgs,
          historyMsgLength,
          modelConfig.compressMessageLengthThreshold,
        );

        if (
          historyMsgLength > modelConfig.compressMessageLengthThreshold &&
          modelConfig.sendMemory
        ) {
          // 在总结时解构max_tokens参数
          const { max_tokens, ...modelcfg } = modelConfig;
          api.llm.chat({
            messages: toBeSummarizedMsgs.concat(
              createMessage({
                role: "system",
                content: Locale.Store.Prompt.Summarize,
                date: "",
              }),
            ),
            config: {
              ...modelcfg,
              stream: true,
              model,
              providerName,
            },
            onUpdate(message) {
              session.memoryPrompt = message;
            },
            onFinish(message, responseRes) {
              if (responseRes?.status === 200) {
                logger.debug("Memory:", message);
                get().updateTargetSession(session, (session) => {
                  session.lastSummarizeIndex = lastSummarizeIndex;
                  session.memoryPrompt = message; // 更新记忆提示并存储到本地存储
                });
              }
            },
            onError(err) {
              logger.error("Summarize error:", err);
            },
          });
        }
      },

      updateStat(message: ChatMessage, session: ChatSession) {
        get().updateTargetSession(session, (session) => {
          session.stat.charCount += message.content.length;
          // TODO: should update chat count and word count
        });
      },
      updateTargetSession(
        targetSession: ChatSession,
        updater: (session: ChatSession) => void,
      ) {
        const sessions = get().sessions;
        const index = sessions.findIndex((s) => s.id === targetSession.id);
        if (index < 0) return;
        updater(sessions[index]);
        set(() => ({ sessions }));
      },
      async clearAllData() {
        await indexedDBStorage.clear();
        localStorage.clear();
        location.reload();
      },
      setLastInput(lastInput: string) {
        set({
          lastInput,
        });
      },

      /** check if the message contains MCP JSON and execute the MCP action */
      checkMcpJson(message: ChatMessage) {
        const mcpEnabled = isMcpEnabled();
        if (!mcpEnabled) return;
        const content = getMessageTextContent(message);
        if (isMcpJson(content)) {
          try {
            const mcpRequest = extractMcpJson(content);
            if (mcpRequest) {
              logger.debug("MCP Request:", mcpRequest);

              executeMcpAction(mcpRequest.clientId, mcpRequest.mcp)
                .then((result) => {
                  logger.debug("MCP Response:", result);
                  const mcpResponse =
                    typeof result === "object"
                      ? JSON.stringify(result)
                      : String(result);
                  get().onUserInput(
                    `\`\`\`json:mcp-response:${mcpRequest.clientId}\n${mcpResponse}\n\`\`\``,
                    [],
                    true,
                  );
                })
                .catch((error) => showToast("MCP execution failed", error));
            }
          } catch (error) {
            logger.error("Check MCP JSON error:", error);
          }
        }
      },
    };

    return methods;
  },
  {
    name: StoreKey.Chat,
    version: 3.3,
    migrate(persistedState, version) {
      const state = persistedState as any;
      const newState = JSON.parse(
        JSON.stringify(state),
      ) as typeof DEFAULT_CHAT_STATE;

      if (version < 2) {
        newState.sessions = [];

        const oldSessions = state.sessions;
        for (const oldSession of oldSessions) {
          const newSession = createEmptySession();
          newSession.topic = oldSession.topic;
          newSession.messages = [...oldSession.messages];
          newSession.mask.modelConfig.sendMemory = true;
          newSession.mask.modelConfig.historyMessageCount = 4;
          newSession.mask.modelConfig.compressMessageLengthThreshold = 1000;
          newState.sessions.push(newSession);
        }
      }

      if (version < 3) {
        // migrate id to nanoid
        newState.sessions.forEach((s) => {
          s.id = nanoid();
          s.messages.forEach((m) => (m.id = nanoid()));
        });
      }

      // Enable `enableInjectSystemPrompts` attribute for old sessions.
      // Resolve issue of old sessions not automatically enabling.
      if (version < 3.1) {
        newState.sessions.forEach((s) => {
          if (
            // Exclude those already set by user
            !s.mask.modelConfig.hasOwnProperty("enableInjectSystemPrompts")
          ) {
            // Because users may have changed this configuration,
            // the user's current configuration is used instead of the default
            const config = useAppConfig.getState();
            s.mask.modelConfig.enableInjectSystemPrompts =
              config.modelConfig.enableInjectSystemPrompts;
          }
        });
      }

      // add default summarize model for every session
      if (version < 3.2) {
        newState.sessions.forEach((s) => {
          const config = useAppConfig.getState();
          s.mask.modelConfig.compressModel = config.modelConfig.compressModel;
          s.mask.modelConfig.compressProviderName =
            config.modelConfig.compressProviderName;
        });
      }
      // revert default summarize model for every session
      if (version < 3.3) {
        newState.sessions.forEach((s) => {
          const config = useAppConfig.getState();
          s.mask.modelConfig.compressModel = "";
          s.mask.modelConfig.compressProviderName = "";
        });
      }

      return newState as any;
    },
  },
);
