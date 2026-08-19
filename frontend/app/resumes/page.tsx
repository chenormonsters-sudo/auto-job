"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "../components/Nav";
import { API_BASE, api } from "../../lib/api";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    api<any[]>("/api/resumes")
      .then((rows) => setResumes(rows))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function upload(file: File) {
    setError("");
    setInfo("");
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/resumes/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "上传失败");
      }
      setInfo("上传成功");
      load();
    } catch (e: any) {
      setError(e.message || "上传失败");
    } finally {
      setBusy(false);
    }
  }

  async function confirm(id: number) {
    setBusy(true);
    try {
      await api(`/api/resumes/${id}/confirm`, { method: "POST" });
      setInfo("已标记为最终确认版");
      load();
    } catch (e: any) {
      setError(e.message || "确认失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Nav />
      <main className="main">
        <div className="page-header">
          <h1>简历管理</h1>
        </div>
        <div className="panel">
          <input type="file" disabled={busy} onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          <p className="muted">支持 PDF / DOCX / TXT / MD，单文件最大 10MB</p>
        </div>
        {error && <div className="error-box">{error}</div>}
        {info && <div className="banner">{info}</div>}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : resumes.length === 0 ? (
          <div className="empty">还没有简历，请先上传一份。</div>
        ) : (
          resumes.map((r) => (
            <div className="item" key={r.id}>
              <div className="item-header">
                <strong>{r.filename}</strong>
                <span className={`status ${r.status}`}>{r.status === "confirmed" ? "已确认" : "草稿"}</span>
                <span className="muted">字符数：{r.structured_json?.char_count ?? "-"}</span>
              </div>
              <div className="action-bar">
                <button className="primary" disabled={busy || r.status === "confirmed"} onClick={() => confirm(r.id)}>
                  标记为最终确认版
                </button>
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
