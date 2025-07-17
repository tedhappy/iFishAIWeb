import React, { useState, useEffect, useRef } from "react";
import styles from "./suggested-questions.module.scss";
import { useChatStore } from "../store/chat";
import { logger } from "../utils/logger";
import {
  getQuestionsByAgentType,
  QuestionConfig,
} from "../config/suggested-questions";

interface Question {
  id: string;
  text: string;
}

// 使用配置文件中的QuestionConfig类型
type QuestionType = QuestionConfig;

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
  userMessage?: string; // 用于生成相关问题
  type?: "default" | "related"; // 问题类型
  sessionId?: string; // 会话ID，用于后端生成推荐问题
  agentType?: string; // Agent类型，用于获取对应的推荐问题
  preloadOnly?: boolean; // 仅预加载，不显示组件
  onPreloadComplete?: (questions: Question[]) => void; // 预加载完成回调
  disableGeneration?: boolean; // 禁用自动生成，只使用缓存
}

// 调用后端API生成推荐问题
async function generateQuestionsFromBackend(
  sessionId: string,
  type: "default" | "related" = "default",
  userMessage?: string,
  agentType?: string,
): Promise<Question[]> {
  try {
    // 获取后端 API 基础 URL
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL || "https://www.ifish.me";
    const response = await fetch(
      `${apiBaseUrl}/flask/agent/suggested-questions`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          type: type,
          user_message: userMessage || "",
        }),
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (data.success && data.questions) {
      return data.questions;
    } else {
      throw new Error(data.error || "生成推荐问题失败");
    }
  } catch (error) {
    logger.error("调用后端生成推荐问题失败:", error);
    // 返回备用问题
    return getFallbackQuestions(type, userMessage, agentType);
  }
}

// 固定的默认推荐问题（新建对话时使用，无需调用后端）
function getFixedDefaultQuestions(agentType?: string): Question[] {
  // 从配置文件获取对应agent的推荐问题
  const configQuestions = getQuestionsByAgentType(agentType);
  return configQuestions.map((q) => ({
    id: q.id,
    text: q.text,
  }));
}

// 备用推荐问题（当后端调用失败时使用）
function getFallbackQuestions(
  type: "default" | "related" = "default",
  userMessage?: string,
  agentType?: string,
): Question[] {
  if (type === "default") {
    // 对于default类型，直接返回固定问题
    return getFixedDefaultQuestions(agentType);
  } else {
    // 根据用户消息和agent类型生成相关问题的备用逻辑
    const message = userMessage?.toLowerCase() || "";
    let relatedQuestions: string[] = [];

    // 首先根据agent类型提供相关问题
    if (agentType === "coding") {
      if (
        message.includes("错误") ||
        message.includes("bug") ||
        message.includes("调试")
      ) {
        relatedQuestions = [
          "如何系统性地调试代码问题？",
          "有哪些常见的编程错误类型？",
          "推荐一些好用的调试工具",
        ];
      } else if (message.includes("性能") || message.includes("优化")) {
        relatedQuestions = [
          "如何分析和优化代码性能？",
          "有哪些常见的性能瓶颈？",
          "推荐一些性能测试工具",
        ];
      } else {
        relatedQuestions = [
          "如何提高代码质量和可维护性？",
          "有哪些最佳编程实践？",
          "推荐一些学习资源和工具",
        ];
      }
    } else if (agentType === "writing") {
      if (message.includes("结构") || message.includes("框架")) {
        relatedQuestions = [
          "如何构建清晰的文章逻辑结构？",
          "有哪些常用的写作框架？",
          "如何让文章更有说服力？",
        ];
      } else if (message.includes("创意") || message.includes("灵感")) {
        relatedQuestions = [
          "如何激发写作创意和灵感？",
          "有哪些创意写作技巧？",
          "如何克服写作瓶颈？",
        ];
      } else {
        relatedQuestions = [
          "如何提高文字表达能力？",
          "有哪些写作风格可以学习？",
          "如何让文章更吸引读者？",
        ];
      }
    } else if (agentType === "business") {
      if (message.includes("策略") || message.includes("规划")) {
        relatedQuestions = [
          "如何制定有效的商业策略？",
          "有哪些战略规划工具？",
          "如何评估策略的可行性？",
        ];
      } else if (message.includes("营销") || message.includes("推广")) {
        relatedQuestions = [
          "有哪些有效的营销策略？",
          "如何选择合适的营销渠道？",
          "如何衡量营销效果？",
        ];
      } else {
        relatedQuestions = [
          "如何提高团队执行力？",
          "有哪些管理工具推荐？",
          "如何应对市场变化？",
        ];
      }
    } else if (agentType === "education") {
      if (message.includes("方法") || message.includes("技巧")) {
        relatedQuestions = [
          "有哪些高效的学习方法？",
          "如何提高学习效率？",
          "如何培养良好的学习习惯？",
        ];
      } else if (message.includes("记忆") || message.includes("背诵")) {
        relatedQuestions = [
          "有哪些提高记忆力的技巧？",
          "如何长期保持知识记忆？",
          "推荐一些记忆训练方法",
        ];
      } else {
        relatedQuestions = [
          "如何制定个人学习计划？",
          "有哪些学习资源推荐？",
          "如何保持学习动力？",
        ];
      }
    } else {
      // 通用agent或未指定类型时的逻辑
      if (message.includes("ai") || message.includes("人工智能")) {
        relatedQuestions = [
          "AI在哪些领域应用最广泛？",
          "AI技术有哪些局限性？",
          "如何学习AI相关知识？",
        ];
      } else if (
        message.includes("编程") ||
        message.includes("代码") ||
        message.includes("code")
      ) {
        relatedQuestions = [
          "如何提高编程技能？",
          "学习编程需要掌握哪些基础知识？",
          "有哪些好的编程实践方法？",
        ];
      } else if (message.includes("学习") || message.includes("教育")) {
        relatedQuestions = [
          "如何制定有效的学习计划？",
          "有哪些高效的学习方法？",
          "如何保持学习动力？",
        ];
      } else if (message.includes("工作") || message.includes("职场")) {
        relatedQuestions = [
          "如何提高工作效率？",
          "有哪些职场沟通技巧？",
          "如何平衡工作与生活？",
        ];
      } else {
        relatedQuestions = [
          "能详细解释一下这个概念吗？",
          "有什么实际应用案例吗？",
          "还有其他相关的信息吗？",
        ];
      }
    }

    return relatedQuestions.map((text, index) => ({
      id: `fallback-related-${index}`,
      text,
    }));
  }
}

// 缓存过期时间（30分钟）
const CACHE_EXPIRE_TIME = 30 * 60 * 1000;

// 检查缓存是否有效
function isCacheValid(timestamp: number): boolean {
  return Date.now() - timestamp < CACHE_EXPIRE_TIME;
}

// 统一的缓存验证函数
function validateCache(
  cache: any,
  sessionId: string,
  userMessage?: string,
): boolean {
  if (!cache) {
    return false;
  }

  // 检查时间戳有效性
  if (!isCacheValid(cache.timestamp)) {
    return false;
  }

  // 检查问题数组有效性
  if (
    !cache.questions ||
    !Array.isArray(cache.questions) ||
    cache.questions.length === 0
  ) {
    return false;
  }

  // 检查会话ID匹配（如果存在）
  if (cache.sessionId && cache.sessionId !== sessionId) {
    return false;
  }

  // 对于相关问题类型，检查用户消息匹配
  if (userMessage !== undefined && cache.userMessage !== userMessage) {
    return false;
  }

  return true;
}

// 清理过期缓存
function clearExpiredCache(chatStore: any, session: any) {
  logger.debug(
    `[推荐问题缓存] 开始清理过期缓存 - 会话ID: ${session?.id || "unknown"}`,
  );

  if (!session?.id) {
    logger.error(
      `[推荐问题缓存] 无效的会话对象，无法清理缓存 - 会话ID: ${session?.id || "unknown"}`,
    );
    return;
  }

  try {
    chatStore.updateTargetSession(session, (session: any) => {
      if (!session.suggestedQuestions) {
        logger.debug(
          `[推荐问题缓存] 无缓存对象需要清理 - 会话ID: ${session.id}`,
        );
        return;
      }

      let clearedCount = 0;
      let invalidCacheCount = 0;
      const types = ["default", "related"] as const;

      types.forEach((type) => {
        const cache = session.suggestedQuestions[type];
        if (cache && !validateCache(cache, session.id)) {
          // 详细检查失败原因用于日志记录
          const isExpired = !isCacheValid(cache.timestamp);
          const isInvalid =
            !cache.questions ||
            !Array.isArray(cache.questions) ||
            cache.questions.length === 0;
          const sessionMismatch =
            cache.sessionId && cache.sessionId !== session.id;

          delete session.suggestedQuestions[type];
          clearedCount++;

          if (isExpired) {
            logger.debug(
              `[推荐问题缓存] 清理过期缓存 - 会话ID: ${session.id}, 类型: ${type}`,
            );
          } else if (isInvalid) {
            logger.debug(
              `[推荐问题缓存] 清理无效缓存 - 会话ID: ${session.id}, 类型: ${type}`,
            );
            invalidCacheCount++;
          } else if (sessionMismatch) {
            logger.debug(
              `[推荐问题缓存] 清理会话ID不匹配的缓存 - 会话ID: ${session.id}, 缓存会话ID: ${cache.sessionId}, 类型: ${type}`,
            );
          }
        }
      });

      // 如果所有缓存都被清理，删除整个缓存对象
      if (Object.keys(session.suggestedQuestions).length === 0) {
        delete session.suggestedQuestions;
        logger.debug(`[推荐问题缓存] 删除空缓存对象 - 会话ID: ${session.id}`);
      }

      if (clearedCount > 0) {
        logger.info(
          `清理缓存完成: sessionId=${session.id}, clearedCount=${clearedCount}, invalidCount=${invalidCacheCount}`,
        );
      } else {
        logger.debug(`[推荐问题缓存] 无需清理的缓存 - 会话ID: ${session.id}`);
      }
    });
  } catch (error) {
    logger.error("清理过期缓存失败:", error);
    logger.error(
      `[推荐问题缓存] 清理过期缓存失败 - 会话ID: ${session?.id || "unknown"}, 错误:`,
      error,
    );
  }
}

// 从会话缓存中获取推荐问题
function getCachedQuestions(
  session: any,
  type: "default" | "related",
  userMessage?: string,
): Question[] | null {
  logger.debug(
    `[推荐问题缓存] 获取缓存 - 会话ID: ${session?.id || "unknown"}, 类型: ${type}, 用户消息: "${userMessage || ""}"`,
  );

  // 增强的会话ID和缓存数据验证
  if (!session?.id || !session?.suggestedQuestions) {
    logger.debug(
      `[推荐问题缓存] 会话ID或缓存数据无效 - 会话ID: ${session?.id || "unknown"}`,
    );
    return null;
  }

  const cache = session.suggestedQuestions[type];

  logger.debug(`[推荐问题缓存] 缓存检查:`, {
    sessionId: session.id,
    type,
    hasCache: !!cache,
    cacheTimestamp: cache?.timestamp,
    cacheUserMessage: cache?.userMessage,
    questionsCount: cache?.questions?.length || 0,
  });

  // 使用统一的缓存验证函数
  const isValid = validateCache(
    cache,
    session.id,
    type === "related" ? userMessage : undefined,
  );

  if (!isValid) {
    logger.debug(
      `[推荐问题缓存] 缓存验证失败 - 会话ID: ${session.id}, 类型: ${type}`,
      {
        hasCache: !!cache,
        timestamp: cache?.timestamp,
        isTimeValid: cache?.timestamp ? isCacheValid(cache.timestamp) : false,
        hasQuestions:
          cache?.questions &&
          Array.isArray(cache.questions) &&
          cache.questions.length > 0,
        sessionMatch: !cache?.sessionId || cache.sessionId === session.id,
        userMessageMatch:
          type === "related" ? cache?.userMessage === userMessage : true,
      },
    );

    // 清理无效缓存
    if (cache && !isCacheValid(cache.timestamp)) {
      delete session.suggestedQuestions[type];
      logger.debug(
        `[推荐问题缓存] 已清理过期缓存 - 会话ID: ${session.id}, 类型: ${type}`,
      );
    }
    return null;
  }

  logger.debug(
    `[推荐问题缓存] 返回有效缓存问题 - 会话ID: ${session.id}, 类型: ${type}, 问题数量: ${cache.questions.length}`,
  );
  return cache.questions;
}

// 将推荐问题保存到会话缓存
function setCachedQuestions(
  chatStore: any,
  session: any,
  type: "default" | "related",
  questions: Question[],
  userMessage?: string,
) {
  logger.debug(
    `[推荐问题缓存] 设置缓存 - 会话ID: ${session?.id || "unknown"}, 类型: ${type}, 问题数量: ${questions.length}, 用户消息: "${userMessage || ""}"`,
  );

  // 增强的输入验证
  if (!session?.id) {
    logger.error(
      `[推荐问题缓存] 无效的会话对象 - 会话ID: ${session?.id || "unknown"}`,
    );
    return;
  }

  if (!questions || !Array.isArray(questions) || questions.length === 0) {
    logger.error(
      `[推荐问题缓存] 无效的问题数组 - 会话ID: ${session.id}, 类型: ${type}`,
    );
    return;
  }

  // 验证问题数据结构
  const validQuestions = questions.filter(
    (q) =>
      q &&
      typeof q.id === "string" &&
      typeof q.text === "string" &&
      q.text.trim(),
  );
  if (validQuestions.length !== questions.length) {
    logger.warn(
      `[推荐问题缓存] 过滤无效问题 - 会话ID: ${session.id}, 原始数量: ${questions.length}, 有效数量: ${validQuestions.length}`,
    );
  }

  if (validQuestions.length === 0) {
    logger.error(
      `[推荐问题缓存] 没有有效问题可缓存 - 会话ID: ${session.id}, 类型: ${type}`,
    );
    return;
  }

  try {
    chatStore.updateTargetSession(session, (session: any) => {
      if (!session.suggestedQuestions) {
        session.suggestedQuestions = {};
        logger.debug(
          `[推荐问题缓存] 初始化会话缓存对象 - 会话ID: ${session.id}`,
        );
      }

      // 清理同类型的过期缓存
      if (
        session.suggestedQuestions[type] &&
        !isCacheValid(session.suggestedQuestions[type].timestamp)
      ) {
        delete session.suggestedQuestions[type];
        logger.debug(
          `[推荐问题缓存] 清理过期缓存 - 会话ID: ${session.id}, 类型: ${type}`,
        );
      }

      const cache = {
        questions: validQuestions,
        timestamp: Date.now(),
        sessionId: session.id, // 添加会话ID标识
        ...(type === "related" && { userMessage: userMessage || "" }),
      };

      logger.debug(`[推荐问题缓存] 缓存对象:`, {
        sessionId: session.id,
        type,
        questionsCount: validQuestions.length,
        timestamp: cache.timestamp,
        userMessage: type === "related" ? userMessage || "" : undefined,
      });

      session.suggestedQuestions[type] = cache;
    });
    logger.info(
      `缓存推荐问题成功: sessionId=${session.id}, type=${type}, count=${validQuestions.length}`,
    );
    logger.debug(
      `[推荐问题缓存] 缓存已保存 - 会话ID: ${session.id}, 类型: ${type}`,
    );
  } catch (error) {
    logger.error("缓存推荐问题失败:", error);
    logger.error(
      `[推荐问题缓存] 缓存保存失败 - 会话ID: ${session?.id || "unknown"}, 类型: ${type}, 错误:`,
      error,
    );
  }
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onQuestionClick,
  type = "default",
  userMessage,
  sessionId,
  agentType,
  preloadOnly = false,
  onPreloadComplete,
  disableGeneration = false,
}) => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const lastRequestRef = useRef<string>("");
  const chatStore = useChatStore();
  const session = chatStore.currentSession();

  // 生成推荐问题
  useEffect(() => {
    const loadQuestions = async () => {
      // 创建请求标识符，避免重复请求
      const requestKey = `${sessionId || ""}_${type}_${userMessage || ""}`;

      logger.debug(
        `[推荐问题组件] 开始加载问题 - 会话ID: ${sessionId || "unknown"}, 类型: ${type}, 用户消息: "${userMessage || ""}", 请求标识: ${requestKey}`,
      );

      // 如果请求参数没有变化，跳过请求
      if (lastRequestRef.current === requestKey) {
        logger.debug(`[推荐问题组件] 跳过重复请求 - 请求标识: ${requestKey}`);
        return;
      }

      lastRequestRef.current = requestKey;

      // 首先检查缓存，如果有缓存则直接使用，不显示loading
      if (session) {
        logger.debug(
          `[推荐问题组件] 检查缓存 - 会话ID: ${session.id}, 类型: ${type}`,
        );
        const cachedQuestions = getCachedQuestions(session, type, userMessage);
        if (cachedQuestions) {
          logger.info(
            `使用缓存的推荐问题: type=${type}, count=${cachedQuestions.length}`,
          );
          logger.debug(
            `[推荐问题组件] 使用缓存问题 - 会话ID: ${session.id}, 类型: ${type}, 问题数量: ${cachedQuestions.length}`,
          );
          setQuestions(cachedQuestions);
          setLoading(false);

          if (preloadOnly && onPreloadComplete) {
            logger.debug(
              `[推荐问题组件] 预加载模式回调 - 会话ID: ${session.id}, 问题数量: ${cachedQuestions.length}`,
            );
            onPreloadComplete(cachedQuestions);
          }
          return;
        }
      }

      // 如果禁用生成且没有缓存，提供默认问题作为后备方案
      if (disableGeneration) {
        logger.debug(
          `[推荐问题组件] 禁用生成模式，无缓存时提供默认问题 - 会话ID: ${sessionId || "unknown"}, 类型: ${type}`,
        );

        // 获取默认问题作为后备方案
        const defaultQuestions = getFixedDefaultQuestions(agentType);
        logger.debug(
          `[推荐问题组件] 禁用生成模式默认问题数量: ${defaultQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
        );

        setQuestions(defaultQuestions);
        setLoading(false);

        if (preloadOnly && onPreloadComplete) {
          onPreloadComplete(defaultQuestions);
        }
        return;
      }

      logger.debug(
        `[推荐问题组件] 缓存未命中，生成新问题 - 会话ID: ${sessionId || "unknown"}, 类型: ${type}`,
      );

      try {
        // 1. 对于default类型，优先使用固定问题（不需要loading）
        if (type === "default") {
          logger.debug(
            `[推荐问题组件] 获取固定默认问题 - 会话ID: ${sessionId || "unknown"}, Agent类型: ${agentType || "unknown"}`,
          );
          const fixedQuestions = getFixedDefaultQuestions(agentType);
          logger.debug(
            `[推荐问题组件] 固定问题数量: ${fixedQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
          );
          setQuestions(fixedQuestions);

          // 如果是预加载模式，调用回调
          if (preloadOnly && onPreloadComplete) {
            logger.debug(
              `[推荐问题组件] 预加载模式回调(固定问题) - 会话ID: ${sessionId || "unknown"}, 问题数量: ${fixedQuestions.length}`,
            );
            onPreloadComplete(fixedQuestions);
          }

          // 缓存固定问题
          if (session) {
            logger.debug(
              `[推荐问题组件] 缓存固定问题 - 会话ID: ${session.id}, 类型: ${type}`,
            );
            setCachedQuestions(chatStore, session, type, fixedQuestions);
          }

          setLoading(false);
          return;
        }

        // 只有在需要调用后端生成问题时才显示loading
        logger.debug(
          `[推荐问题组件] 开始后端生成流程 - 会话ID: ${sessionId || "unknown"}, 类型: ${type}`,
        );
        setLoading(true);

        // 2. 调用后端生成新问题（只有在没有缓存时才会执行到这里）
        // 如果是related类型但没有userMessage，则降级为default类型
        const actualType =
          type === "related" && (!userMessage || !userMessage.trim())
            ? "default"
            : type;
        const actualUserMessage =
          actualType === "default" ? undefined : userMessage;

        logger.debug(
          `[推荐问题组件] 实际类型: ${actualType}, 实际用户消息: "${actualUserMessage || ""}" - 会话ID: ${sessionId || "unknown"}`,
        );

        const generatedQuestions = await generateQuestionsFromBackend(
          sessionId || "", // 传递空字符串而不是undefined
          actualType,
          actualUserMessage,
          agentType,
        );

        logger.debug(
          `[推荐问题组件] 后端返回问题数量: ${generatedQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
        );

        // 如果类型被降级了，记录日志
        if (actualType !== type) {
          logger.info(
            `推荐问题类型从 ${type} 降级为 ${actualType}，因为缺少用户消息`,
          );
          logger.debug(
            `[推荐问题组件] 类型降级: ${type} -> ${actualType} - 会话ID: ${sessionId || "unknown"}`,
          );
        }

        let finalQuestions: Question[];
        if (generatedQuestions.length > 0) {
          // 去重处理
          const uniqueQuestions = generatedQuestions.filter(
            (question, index, self) =>
              index === self.findIndex((q) => q.text === question.text),
          );
          finalQuestions = uniqueQuestions;
          logger.debug(
            `[推荐问题组件] 去重后问题数量: ${finalQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
          );
        } else {
          // 使用备用问题
          logger.debug(
            `[推荐问题组件] 使用备用问题 - 会话ID: ${sessionId || "unknown"}`,
          );
          finalQuestions = getFallbackQuestions(type, userMessage, agentType);
          logger.debug(
            `[推荐问题组件] 备用问题数量: ${finalQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
          );
        }

        logger.debug(
          `[推荐问题组件] 设置最终问题 - 会话ID: ${sessionId || "unknown"}, 类型: ${actualType}, 问题数量: ${finalQuestions.length}`,
        );
        setQuestions(finalQuestions);

        // 如果是预加载模式，调用回调
        if (preloadOnly && onPreloadComplete) {
          logger.debug(
            `[推荐问题组件] 预加载模式回调(生成问题) - 会话ID: ${sessionId || "unknown"}, 问题数量: ${finalQuestions.length}`,
          );
          onPreloadComplete(finalQuestions);
        }

        // 缓存生成的问题
        if (session) {
          logger.debug(
            `[推荐问题组件] 缓存生成的问题 - 会话ID: ${session.id}, 类型: ${actualType}`,
          );
          setCachedQuestions(
            chatStore,
            session,
            actualType,
            finalQuestions,
            actualUserMessage,
          );
        }
      } catch (error) {
        logger.error("生成推荐问题失败:", error);
        logger.debug(
          `[推荐问题组件] 生成失败，使用备用问题 - 会话ID: ${sessionId || "unknown"}, 错误:`,
          error,
        );
        // 使用备用问题
        const fallbackQuestions = getFallbackQuestions(
          type,
          userMessage,
          agentType,
        );
        logger.debug(
          `[推荐问题组件] 错误备用问题数量: ${fallbackQuestions.length} - 会话ID: ${sessionId || "unknown"}`,
        );
        setQuestions(fallbackQuestions);

        if (preloadOnly && onPreloadComplete) {
          logger.debug(
            `[推荐问题组件] 预加载模式回调(错误备用) - 会话ID: ${sessionId || "unknown"}, 问题数量: ${fallbackQuestions.length}`,
          );
          onPreloadComplete(fallbackQuestions);
        }
      } finally {
        setLoading(false);
        logger.debug(
          `[推荐问题组件] 加载完成 - 会话ID: ${sessionId || "unknown"}, 类型: ${type}`,
        );
      }
    };

    loadQuestions();
  }, [
    sessionId,
    type,
    userMessage,
    preloadOnly,
    onPreloadComplete,
    agentType,
    disableGeneration,
  ]);

  // 如果是预加载模式，不渲染任何内容
  if (preloadOnly) {
    return null;
  }

  // 移除loading显示，但保持loading逻辑
  // if (loading) {
  //   return (
  //     <div className={styles["suggested-questions"]}>
  //       <div className={styles["suggested-questions-title"]}>
  //         <span className={styles["title-icon"]}>💡</span>
  //         <span>相关问题</span>
  //       </div>
  //       <div className={styles["loading-text"]}>
  //         正在生成推荐问题，也可以直接输入问题
  //       </div>
  //     </div>
  //   );
  // }

  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className={styles["suggested-questions"]}>
      <div className={styles["suggested-questions-title"]}>
        <span className={styles["title-icon"]}>💡</span>
        <span>相关问题</span>
      </div>
      <div className={styles["questions-container"]}>
        {questions.map((question) => (
          <button
            key={question.id}
            className={styles["question-item"]}
            onClick={() => onQuestionClick(question.text)}
            type="button"
          >
            <span className={styles["question-text"]}>{question.text}</span>
            <div className={styles["question-arrow"]}>→</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;

// 导出生成函数供外部使用
export { generateQuestionsFromBackend, getFallbackQuestions, validateCache };
