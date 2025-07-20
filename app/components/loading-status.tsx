import React, { useState, useEffect } from "react";
import { LoadingIcon } from "./ui-lib";
import styles from "./loading-status.module.scss";

export interface LoadingStatusProps {
  isLoading: boolean;
  stage?:
    | "connecting"
    | "processing"
    | "generating"
    | "thinking"
    | "error"
    | "tool_calling";
  message?: string;
  estimatedTime?: number;
  onCancel?: () => void;
  onRetry?: () => void;
  showProgress?: boolean;
}

export function LoadingStatus({
  isLoading,
  stage = "connecting",
  message,
  estimatedTime,
  onCancel,
  onRetry,
  showProgress = true,
}: LoadingStatusProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [progress, setProgress] = useState(0);
  const [cancelButtonShown, setCancelButtonShown] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setElapsedTime(0);
      setProgress(0);
      setCancelButtonShown(false);
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedTime(elapsed);

      // 1秒后显示取消按钮，一旦显示就不再隐藏
      if (elapsed > 1 && !cancelButtonShown) {
        setCancelButtonShown(true);
      }

      // 模拟进度条（基于预估时间）
      if (estimatedTime && showProgress) {
        const progressPercent = Math.min((elapsed / estimatedTime) * 100, 95);
        setProgress(progressPercent);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isLoading, estimatedTime, showProgress, cancelButtonShown]);

  if (!isLoading) return null;

  const getStageMessage = () => {
    if (message) return message;

    switch (stage) {
      case "connecting":
        return "正在连接服务器...";
      case "processing":
        return "正在处理请求...";
      case "thinking":
        return "正在努力思考...";
      case "generating":
        return "正在生成回复...";
      case "tool_calling":
        return "正在调用工具...";
      case "error":
        return "连接出现问题";
      default:
        return "正在加载...";
    }
  };

  const getTimeDisplay = () => {
    if (elapsedTime < 60) {
      return `${elapsedTime}秒`;
    }
    const minutes = Math.floor(elapsedTime / 60);
    const seconds = elapsedTime % 60;
    return `${minutes}分${seconds}秒`;
  };

  // 根据当前阶段获取取消按钮的配置
  const getCancelButtonConfig = () => {
    // 按钮文字始终显示"取消"，但根据阶段触发不同逻辑
    return {
      text: "取消",
      action: () => {
        // 根据当前阶段执行不同的逻辑
        switch (stage) {
          case "thinking":
            // 思考阶段：停止思考
            onCancel?.();
            break;
          case "error":
            // 错误阶段：也是取消，不是重试（已经有单独的重试按钮）
            onCancel?.();
            break;
          default:
            // 其他阶段：普通取消
            onCancel?.();
            break;
        }
      },
    };
  };

  const shouldShowRetry = false; // 隐藏重试按钮

  return (
    <div className={styles["loading-status"]}>
      <div className={styles["loading-content"]}>
        <div className={styles["loading-icon"]}>
          {stage === "error" ? (
            <div className={styles["error-icon"]}>⚠️</div>
          ) : (
            <LoadingIcon />
          )}
        </div>

        <div className={styles["loading-text"]}>
          <div className={styles["stage-message"]}>{getStageMessage()}</div>
          <div className={styles["time-display"]}>
            已等待: {getTimeDisplay()}
          </div>

          {estimatedTime && showProgress && stage !== "error" && (
            <div className={styles["progress-container"]}>
              <div className={styles["progress-bar"]}>
                <div
                  className={styles["progress-fill"]}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className={styles["progress-text"]}>
                预计还需 {Math.max(0, estimatedTime - elapsedTime)}秒
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={styles["loading-actions"]}>
        {cancelButtonShown && (
          <button
            className={styles["action-button"]}
            onClick={getCancelButtonConfig().action}
          >
            {getCancelButtonConfig().text}
          </button>
        )}

        {shouldShowRetry && onRetry && (
          <button
            className={styles["action-button"] + " " + styles["retry-button"]}
            onClick={onRetry}
          >
            重试
          </button>
        )}
      </div>
    </div>
  );
}
