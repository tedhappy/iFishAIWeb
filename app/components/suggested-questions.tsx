import React from "react";
import styles from "./suggested-questions.module.scss";
import LightningIcon from "../icons/lightning.svg";

export interface SuggestedQuestion {
  id: string;
  text: string;
}

export interface SuggestedQuestionsProps {
  questions: SuggestedQuestion[];
  onQuestionClick: (question: string) => void;
  title?: string;
  className?: string;
}

export function SuggestedQuestions({
  questions,
  onQuestionClick,
  title = "相关问题",
  className = "",
}: SuggestedQuestionsProps) {
  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className={`${styles["suggested-questions"]} ${className}`}>
      {title && (
        <div className={styles["suggested-questions-title"]}>
          <LightningIcon className={styles["title-icon"]} />
          <span>{title}</span>
        </div>
      )}
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
}

// 默认推荐问题生成器
export function generateDefaultQuestions(): SuggestedQuestion[] {
  const defaultQuestions = [
    "AI技术的发展会给我们的生活带来哪些改变？",
    "AI未来的发展趋势是什么？",
    "如何正确引导AI技术的发展？",
  ];

  return defaultQuestions.map((text, index) => ({
    id: `default-${index}`,
    text,
  }));
}

// 根据用户消息生成相关问题
export function generateRelatedQuestions(
  userMessage: string,
): SuggestedQuestion[] {
  // 这里可以根据用户消息的内容生成相关问题
  // 目前使用简单的关键词匹配逻辑，后续可以集成AI生成
  const message = userMessage.toLowerCase();

  let relatedQuestions: string[] = [];

  if (message.includes("ai") || message.includes("人工智能")) {
    relatedQuestions = [
      "AI在哪些领域应用最广泛？",
      "AI技术有哪些局限性？",
      "如何学习AI相关知识？",
    ];
  } else if (message.includes("编程") || message.includes("代码")) {
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
    // 通用相关问题
    relatedQuestions = [
      "能详细解释一下这个概念吗？",
      "有什么实际应用案例吗？",
      "还有其他相关的信息吗？",
    ];
  }

  return relatedQuestions.map((text, index) => ({
    id: `related-${Date.now()}-${index}`,
    text,
  }));
}
