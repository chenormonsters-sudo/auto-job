"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Nav from "./components/Nav";
import { api } from "../lib/api";

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>("/api/health")
      .then(setHealth)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <Nav />
      <main className="main">
        <h1>Resume Job Workbench</h1>
        <p className="muted">免费、本地优先的国内多平台求职助手。</p>
        {error && <p className="danger">{error}</p>}
        {health && (
          <div className="panel">
            <div>后端状态：{health.status}</div>
            <div>最小投递间隔：{health.min_delivery_interval_seconds} 秒</div>
            <div>指纹伪装：{health.fingerprint_spoofing_enabled ? "开启" : "关闭"}</div>
          </div>
        )}
        <div className="grid">
          <Link href="/resumes" className="panel">简历上传与确认</Link>
          <Link href="/jobs" className="panel">JD 管理与匹配</Link>
          <Link href="/review" className="panel">AI 简历审查</Link>
          <Link href="/delivery" className="panel">投递确认队列</Link>
        </div>
      </main>
    </div>
  );
}
