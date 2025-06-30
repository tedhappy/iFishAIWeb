import React, { Fragment, useEffect, useMemo, useRef, useState } from "react";

import styles from "./home.module.scss";

import { IconButton } from "./button";
import SettingsIcon from "../icons/settings.svg";
import AddIcon from "../icons/add.svg";
import DeleteIcon from "../icons/delete.svg";
import DragIcon from "../icons/drag.svg";
import GithubIcon from "../icons/github.svg";

import Locale from "../locales";

import { useAppConfig, useChatStore } from "../store";

import {
  DEFAULT_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH,
  MIN_SIDEBAR_WIDTH,
  NARROW_SIDEBAR_WIDTH,
  Path,
} from "../constant";

import { useNavigate } from "react-router-dom";
import { isIOS, useMobileScreen } from "../utils";
import dynamic from "next/dynamic";
import { Selector, showConfirm, Modal } from "./ui-lib";
import clsx from "clsx";
import { isMcpEnabled } from "../mcp/actions";
import { useAccessStore } from "../store/access";

const DISCOVERY = [
  { name: Locale.Plugin.Name, path: Path.Plugins },
  { name: "Stable Diffusion", path: Path.Sd },
  { name: Locale.SearchChat.Page.Title, path: Path.SearchChat },
];

const ChatList = dynamic(async () => (await import("./chat-list")).ChatList, {
  loading: () => null,
});

export function useHotKey() {
  const chatStore = useChatStore();

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey) {
        if (e.key === "ArrowUp") {
          chatStore.nextSession(-1);
        } else if (e.key === "ArrowDown") {
          chatStore.nextSession(1);
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });
}

export function useDragSideBar() {
  const limit = (x: number) => Math.min(MAX_SIDEBAR_WIDTH, x);

  const config = useAppConfig();
  const startX = useRef(0);
  const startDragWidth = useRef(config.sidebarWidth ?? DEFAULT_SIDEBAR_WIDTH);
  const lastUpdateTime = useRef(Date.now());

  const toggleSideBar = () => {
    config.update((config) => {
      if (config.sidebarWidth < MIN_SIDEBAR_WIDTH) {
        config.sidebarWidth = DEFAULT_SIDEBAR_WIDTH;
      } else {
        config.sidebarWidth = NARROW_SIDEBAR_WIDTH;
      }
    });
  };

  const onDragStart = (e: MouseEvent) => {
    startX.current = e.clientX;
    startDragWidth.current = config.sidebarWidth;
    const dragStartTime = Date.now();

    const handleDragMove = (e: MouseEvent) => {
      if (Date.now() < lastUpdateTime.current + 20) {
        return;
      }
      lastUpdateTime.current = Date.now();
      const d = e.clientX - startX.current;
      const nextWidth = limit(startDragWidth.current + d);
      config.update((config) => {
        if (nextWidth < MIN_SIDEBAR_WIDTH) {
          config.sidebarWidth = NARROW_SIDEBAR_WIDTH;
        } else {
          config.sidebarWidth = nextWidth;
        }
      });
    };

    const handleDragEnd = () => {
      window.removeEventListener("pointermove", handleDragMove);
      window.removeEventListener("pointerup", handleDragEnd);
      const shouldFireClick = Date.now() - dragStartTime < 300;
      if (shouldFireClick) {
        toggleSideBar();
      }
    };

    window.addEventListener("pointermove", handleDragMove);
    window.addEventListener("pointerup", handleDragEnd);
  };

  const isMobileScreen = useMobileScreen();
  const shouldNarrow =
    !isMobileScreen && config.sidebarWidth < MIN_SIDEBAR_WIDTH;

  useEffect(() => {
    const barWidth = shouldNarrow
      ? NARROW_SIDEBAR_WIDTH
      : limit(config.sidebarWidth ?? DEFAULT_SIDEBAR_WIDTH);
    const sideBarWidth = isMobileScreen ? "100vw" : `${barWidth}px`;
    document.documentElement.style.setProperty("--sidebar-width", sideBarWidth);
  }, [config.sidebarWidth, isMobileScreen, shouldNarrow]);

  return {
    onDragStart,
    shouldNarrow,
  };
}

export function SideBarContainer(props: {
  children: React.ReactNode;
  onDragStart: (e: MouseEvent) => void;
  shouldNarrow: boolean;
  className?: string;
}) {
  const isMobileScreen = useMobileScreen();
  const isIOSMobile = useMemo(
    () => isIOS() && isMobileScreen,
    [isMobileScreen],
  );
  const { children, className, onDragStart, shouldNarrow } = props;
  return (
    <div
      className={clsx(styles.sidebar, className, {
        [styles["narrow-sidebar"]]: shouldNarrow,
      })}
      style={{
        // #3016 disable transition on ios mobile screen
        transition: isMobileScreen && isIOSMobile ? "none" : undefined,
      }}
    >
      {children}
      <div
        className={styles["sidebar-drag"]}
        onPointerDown={(e) => onDragStart(e as any)}
      >
        <DragIcon />
      </div>
    </div>
  );
}

export function SideBarHeader(props: {
  title?: string | React.ReactNode;
  subTitle?: string | React.ReactNode;
  logo?: React.ReactNode;
  children?: React.ReactNode;
  shouldNarrow?: boolean;
}) {
  const { title, subTitle, logo, children, shouldNarrow } = props;
  return (
    <Fragment>
      <div
        className={clsx(styles["sidebar-header"], {
          [styles["sidebar-header-narrow"]]: shouldNarrow,
        })}
        data-tauri-drag-region
      >
        <div className={styles["sidebar-title-container"]}>
          <div className={styles["sidebar-title"]} data-tauri-drag-region>
            {title}
          </div>
          <div className={styles["sidebar-sub-title"]}>{subTitle}</div>
        </div>
        <div className={clsx(styles["sidebar-logo"], "no-dark")}>{logo}</div>
      </div>
      {children}
    </Fragment>
  );
}

export function SideBarBody(props: {
  children: React.ReactNode;
  onClick?: (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => void;
}) {
  const { onClick, children } = props;
  return (
    <div className={styles["sidebar-body"]} onClick={onClick}>
      {children}
    </div>
  );
}

function AuthorModal(props: { onClose: () => void }) {
  return (
    <div className="modal-mask">
      <Modal
        title="关于作者"
        onClose={props.onClose}
        actions={[
          <IconButton
            key="close"
            onClick={props.onClose}
            text="关闭"
            bordered
          />,
        ]}
      >
        <div style={{ padding: "16px 0", textAlign: "center", fontSize: 16 }}>
          <div>作者：小鱼AI聊天助手</div>
          <div>邮箱：fishaiweb@outlook.com</div>
          <div>微信：fishaiweb</div>
        </div>
      </Modal>
    </div>
  );
}

export function SideBarTail(props: {
  primaryAction?: React.ReactNode;
  secondaryAction?: React.ReactNode;
  shouldNarrow?: boolean;
}) {
  const { primaryAction, secondaryAction, shouldNarrow } = props;
  const [showAuthor, setShowAuthor] = useState(false);

  return (
    <div className={styles["sidebar-tail"]}>
      <div className={styles["sidebar-actions"]}>
        {/* 设置按钮 */}
        {primaryAction && Array.isArray(primaryAction)
          ? primaryAction[1]
          : primaryAction}
        {/* 关于作者按钮 */}
        <IconButton
          icon={<GithubIcon />}
          text={shouldNarrow ? undefined : "关于"}
          bordered
          onClick={() => setShowAuthor(true)}
        />
        {/* 新的助手按钮 */}
        {secondaryAction}
      </div>
      {showAuthor && <AuthorModal onClose={() => setShowAuthor(false)} />}
    </div>
  );
}

export function SideBar(props: { className?: string }) {
  useHotKey();
  const { onDragStart, shouldNarrow } = useDragSideBar();
  const [showDiscoverySelector, setshowDiscoverySelector] = useState(false);
  const navigate = useNavigate();
  const config = useAppConfig();
  const chatStore = useChatStore();
  const [mcpEnabled, setMcpEnabled] = useState(false);
  const accessStore = useAccessStore();
  const isAdmin = accessStore.accessCode === "admin";

  const [showPwdModal, setShowPwdModal] = useState(false);
  const [inputPwd, setInputPwd] = useState("");
  const [pwdError, setPwdError] = useState("");

  const handleSettingsClick = () => {
    setShowPwdModal(true);
    setInputPwd("");
    setPwdError("");
  };

  const handlePwdConfirm = async () => {
    try {
      const res = await fetch("/api/verify-admin-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: inputPwd }),
      });
      const data = await res.json();
      if (data.ok) {
        setShowPwdModal(false);
        navigate(Path.Settings);
      } else {
        setPwdError("密码错误，请重试！");
      }
    } catch (e) {
      setPwdError("网络异常，请稍后重试！");
    }
  };

  useEffect(() => {
    // 检查 MCP 是否启用
    const checkMcpStatus = async () => {
      const enabled = await isMcpEnabled();
      setMcpEnabled(enabled);
      console.log("[SideBar] MCP enabled:", enabled);
    };
    checkMcpStatus();
  }, []);

  return (
    <SideBarContainer
      onDragStart={onDragStart}
      shouldNarrow={shouldNarrow}
      {...props}
    >
      <SideBarHeader
        title="小鱼AI聊天助手"
        subTitle="你好，我是小鱼，你的智能聊天助手。"
        logo={
          <img
            src="/android-chrome-192x192.png"
            alt="logo"
            style={{ width: 48, height: 48, borderRadius: 12 }}
          />
        }
        shouldNarrow={shouldNarrow}
      >
        {/* 隐藏顶部红框按钮：面具、发现 */}
        {/* <div className={styles["sidebar-header-bar"]}>
          <IconButton
            icon={<MaskIcon />}
            text={shouldNarrow ? undefined : Locale.Mask.Name}
            className={styles["sidebar-bar-button"]}
            onClick={() => {
              if (config.dontShowMaskSplashScreen !== true) {
                navigate(Path.NewChat, { state: { fromHome: true } });
              } else {
                navigate(Path.Masks, { state: { fromHome: true } });
              }
            }}
            shadow
          />
          {mcpEnabled && (
            <IconButton
              icon={<McpIcon />}
              text={shouldNarrow ? undefined : Locale.Mcp.Name}
              className={styles["sidebar-bar-button"]}
              onClick={() => {
                navigate(Path.McpMarket, { state: { fromHome: true } });
              }}
              shadow
            />
          )}
          <IconButton
            icon={<DiscoveryIcon />}
            text={shouldNarrow ? undefined : Locale.Discovery.Name}
            className={styles["sidebar-bar-button"]}
            onClick={() => setshowDiscoverySelector(true)}
            shadow
          />
        </div> */}
        {/* 隐藏结束 */}
        {showDiscoverySelector && (
          <Selector
            items={[
              ...DISCOVERY.map((item) => {
                return {
                  title: item.name,
                  value: item.path,
                };
              }),
            ]}
            onClose={() => setshowDiscoverySelector(false)}
            onSelection={(s) => {
              navigate(s[0], { state: { fromHome: true } });
            }}
          />
        )}
      </SideBarHeader>
      <SideBarBody
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            navigate(Path.Home);
          }
        }}
      >
        <ChatList narrow={shouldNarrow} />
      </SideBarBody>
      <SideBarTail
        primaryAction={
          <>
            <div className={clsx(styles["sidebar-action"], styles.mobile)}>
              <IconButton
                icon={<DeleteIcon />}
                onClick={async () => {
                  if (await showConfirm(Locale.Home.DeleteChat)) {
                    chatStore.deleteSession(chatStore.currentSessionIndex);
                  }
                }}
              />
            </div>
            {/* 所有用户都可见设置按钮，点击弹出密码弹窗 */}
            <div
              className={styles["sidebar-action"]}
              onClick={handleSettingsClick}
            >
              <IconButton
                aria={Locale.Settings.Title}
                icon={<SettingsIcon />}
                text={shouldNarrow ? undefined : Locale.Settings.Title}
                bordered
                shadow
              />
            </div>
            {/* 密码弹窗，全屏遮罩+内容居中，体验与登录页一致 */}
            {showPwdModal && (
              <div
                style={{
                  position: "fixed",
                  zIndex: 99999,
                  left: 0,
                  top: 0,
                  right: 0,
                  bottom: 0,
                  background: "rgba(0,0,0,0.3)",
                  backdropFilter: "blur(2px)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    background: "#fff",
                    borderRadius: 8,
                    padding: 32,
                    boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                    minWidth: 320,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <div style={{ fontSize: 18, marginBottom: 16 }}>
                    请输入管理员密码
                  </div>
                  <input
                    type="password"
                    value={inputPwd}
                    onChange={(e) => setInputPwd(e.target.value)}
                    style={{
                      padding: "10px 16px",
                      fontSize: 16,
                      borderRadius: 6,
                      border: "1px solid #eee",
                      marginBottom: 8,
                      width: "100%",
                      maxWidth: 320,
                    }}
                  />
                  {pwdError && (
                    <div style={{ color: "red", marginBottom: 8 }}>
                      {pwdError}
                    </div>
                  )}
                  <button
                    onClick={handlePwdConfirm}
                    style={{
                      padding: "10px 32px",
                      background: "#1890aa",
                      color: "#fff",
                      border: "none",
                      borderRadius: "8px",
                      fontSize: "16px",
                      cursor: "pointer",
                      marginTop: 8,
                      width: "100%",
                      maxWidth: 320,
                    }}
                  >
                    确认
                  </button>
                  {/* 关闭按钮 */}
                  <button
                    onClick={() => setShowPwdModal(false)}
                    style={{
                      marginTop: 16,
                      background: "none",
                      border: "none",
                      color: "#888",
                      fontSize: 14,
                      cursor: "pointer",
                    }}
                  >
                    取消
                  </button>
                </div>
              </div>
            )}
          </>
        }
        secondaryAction={
          <IconButton
            icon={<AddIcon />}
            text={shouldNarrow ? undefined : Locale.Home.NewChat}
            onClick={() => {
              if (config.dontShowMaskSplashScreen) {
                chatStore.newSession();
                navigate(Path.Chat);
              } else {
                navigate(Path.NewChat);
              }
            }}
            shadow
          />
        }
        shouldNarrow={shouldNarrow}
      />
    </SideBarContainer>
  );
}
