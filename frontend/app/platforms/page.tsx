"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../../lib/api";

const PLATFORM_NAMES: Record<string, string> = {
  boss: "Boss直聘",
  liepin: "猎聘",
  zhilian: "智联招聘",
  job51: "前程无忧",
};

export default function PlatformsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [form, setForm] = useState<Record<string, { login_method: string; profile_path: string; cookie: string }>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loginPlatform, setLoginPlatform] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    api<any[]>("/api/platforms")
      .then((rows) => {
        setAccounts(rows);
        setForm((prev) => {
          const next = { ...prev };
          for (const row of rows) {
            next[row.platform] = next[row.platform] || {
              login_method: row.login_method || "qr",
              profile_path: row.profile_path || "",
              cookie: "",
            };
          }
          return next;
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  function update(platform: string, key: string, value: string) {
    setForm((prev) => ({
      ...prev,
      [platform]: { ...(prev[platform] || { login_method: "qr", profile_path: "", cookie: "" }), [key]: value },
    }));
  }

  async function save(platform: string) {
    const entry = form[platform];
    if (!entry) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await api(`/api/platforms/${platform}/account`, {
        method: "PUT",
        body: JSON.stringify(entry),
      });
      setInfo(`${PLATFORM_NAMES[platform] || platform} 配置已保存，Cookie 已加密`);
      load();
    } catch (e: any) {
      setError(e.message || "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function pollQrStatus(platform: string) {
    for (let i = 0; i < 70; i++) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const state = await api<any>(`/api/platforms/${platform}/qr-status`);
      if (!state.running) {
        setLoginPlatform("");
        load();
        if (state.account_status === "configured") {
          setInfo("登录态已保存到浏览器用户目录");
        } else {
          setError("未检测到登录完成，请重试");
        }
        return;
      }
    }
    setLoginPlatform("");
    setError("扫码登录超时");
  }

  async function openQrLogin(platform: string) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await api(`/api/platforms/${platform}/qr-login`, { method: "POST" });
      setLoginPlatform(platform);
      setInfo(`${PLATFORM_NAMES[platform] || platform} 登录窗口已打开，扫码登录后请关闭浏览器窗口`);
      await pollQrStatus(platform);
    } catch (e: any) {
      setError(e.message || "打开扫码登录失败");
      setLoginPlatform("");
    } finally {
      setBusy(false);
    }
  }

  async function openDefaultLogin(platform: string) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await api(`/api/platforms/${platform}/open-login`, { method: "POST" });
      setInfo(`${PLATFORM_NAMES[platform] || platform} 已用默认浏览器打开，登录后请复制 Cookie 粘贴到上面保存`);
    } catch (e: any) {
      setError(e.message || "打开登录页失败");
    } finally {
      setBusy(false);
    }
  }

  async function clear(platform: string) {
    if (!window.confirm(`确定清除 ${PLATFORM_NAMES[platform] || platform} 的登录配置吗？`)) {
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await api(`/api/platforms/${platform}/account`, { method: "DELETE" });
      setInfo(`${PLATFORM_NAMES[platform] || platform} 配置已清除`);
      load();
    } catch (e: any) {
      setError(e.message || "清除失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Nav />
      <main className="main">
        <div className="page-header">
          <h1>平台账号</h1>
        </div>
        <div className="banner">
          优先使用浏览器用户目录保持登录态；也可粘贴 Cookie。Cookie 会用本机密钥加密存储，不会上传到第三方。扫码窗口受平台风控影响，请勿打开 F12；若反复验证，请改用 Cookie 方式。
        </div>
        {error && <div className="error-box">{error}</div>}
        {info && <div className="banner">{info}</div>}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : accounts.length === 0 ? (
          <div className="empty">暂无可用平台。</div>
        ) : (
          <div className="grid">
            {accounts.map((account) => (
              <div className="item" key={account.platform}>
                <div className="item-header">
                  <strong>{PLATFORM_NAMES[account.platform] || account.platform}</strong>
                  <span className={`status ${account.status === "configured" ? "confirmed" : "pending_confirm"}`}>
                    {account.status === "configured" ? "已配置" : "未配置"}
                  </span>
                </div>
                <label className="field">
                  登录方式
                  <select
                    value={form[account.platform]?.login_method || "qr"}
                    onChange={(e) => update(account.platform, "login_method", e.target.value)}
                  >
                    <option value="qr">扫码登录</option>
                    <option value="cookie">Cookie</option>
                    <option value="profile">浏览器用户目录</option>
                  </select>
                </label>
                <label className="field">
                  浏览器用户目录（可选）
                  <input
                    placeholder="例如 C:\Users\name\AppData\Local\Google\Chrome\User Data\Profile 1"
                    value={form[account.platform]?.profile_path || ""}
                    onChange={(e) => update(account.platform, "profile_path", e.target.value)}
                  />
                </label>
                <label className="field">
                  Cookie（可选，加密存储）
                  <textarea
                    rows={3}
                    placeholder="粘贴平台登录后的 Cookie 字符串"
                    value={form[account.platform]?.cookie || ""}
                    onChange={(e) => update(account.platform, "cookie", e.target.value)}
                  />
                </label>
                <div className="action-bar">
                  <button className="primary" disabled={busy} onClick={() => save(account.platform)}>
                    保存配置
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={busy || loginPlatform === account.platform}
                    onClick={() => openQrLogin(account.platform)}
                  >
                    {loginPlatform === account.platform ? "等待扫码..." : "扫码登录"}
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => openDefaultLogin(account.platform)}>
                    默认浏览器打开
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => clear(account.platform)}>
                    清除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
