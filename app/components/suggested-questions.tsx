import React, { useState, useEffect, useRef } from "react";
import styles from "./suggested-questions.module.scss";

interface Question {
  id: string;
  text: string;
}

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
  userMessage?: string; // 用于生成相关问题
  type?: "default" | "related"; // 问题类型
  sessionId?: string; // 会话ID，用于后端生成推荐问题
}

// 调用后端API生成推荐问题
async function generateQuestionsFromBackend(
  sessionId: string,
  type: "default" | "related" = "default",
  userMessage?: string,
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
    console.error("调用后端生成推荐问题失败:", error);
    // 返回备用问题
    return getFallbackQuestions(type, userMessage);
  }
}

// 备用推荐问题（当后端调用失败时使用）
function getFallbackQuestions(
  type: "default" | "related" = "default",
  userMessage?: string,
): Question[] {
  if (type === "default") {
    const defaultQuestions = [
      "AI技术的发展会给我们的生活带来哪些改变？",
      "如何提高工作效率和学习能力？",
      "有什么实用的生活小技巧可以分享？",
    ];
    return defaultQuestions.map((text, index) => ({
      id: `fallback-default-${index}`,
      text,
    }));
  } else {
    // 根据用户消息生成相关问题的备用逻辑
    const message = userMessage?.toLowerCase() || "";
    let relatedQuestions: string[] = [];

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
    } else {
      relatedQuestions = [
        "能详细解释一下这个概念吗？",
        "有什么实际应用案例吗？",
        "还有其他相关的信息吗？",
      ];
    }

    return relatedQuestions.map((text, index) => ({
      id: `fallback-related-${index}`,
      text,
    }));
  }
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onQuestionClick,
  userMessage,
  type = "default",
  sessionId,
}) => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const lastRequestRef = useRef<string>("");

  // 生成推荐问题
  useEffect(() => {
    const loadQuestions = async () => {
      // 创建请求标识符，避免重复请求
      const requestKey = `${sessionId || ""}_${type}_${userMessage || ""}`;

      // 如果请求参数没有变化，跳过请求
      if (lastRequestRef.current === requestKey) {
        return;
      }

      lastRequestRef.current = requestKey;
      setLoading(true);

      try {
        // 即使没有sessionId，也尝试调用后端生成推荐问题
        // 后端已经支持在sessionId为空时返回默认推荐问题
        const generatedQuestions = await generateQuestionsFromBackend(
          sessionId || "", // 传递空字符串而不是undefined
          type,
          userMessage,
        );
        setQuestions(generatedQuestions);
      } catch (error) {
        console.error("加载推荐问题失败:", error);
        setQuestions(getFallbackQuestions(type, userMessage));
      } finally {
        setLoading(false);
      }
    };

    loadQuestions();
  }, [sessionId, type, userMessage]);

  if (loading) {
    return (
      <div className={styles["suggested-questions"]}>
        <div className={styles["suggested-questions-title"]}>
          <span className={styles["title-icon"]}>💡</span>
          <span>相关问题</span>
        </div>
        <div className={styles["questions-container"]}>正在生成推荐问题...</div>
      </div>
    );
  }

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
export { generateQuestionsFromBackend, getFallbackQuestions };
