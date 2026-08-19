"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../../lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [resumes, setResumes] = useState<any[]>([]);
  const [form, setForm] = useState({ platform: "manual", company: "", title: "", url: "", jd_text: "" });
  const [resumeId, setResumeId] = useState<number>(0);
  const [allowLlm, setAllowLlm] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [searchCity, setSearchCity] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const [searchError, setSearchError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([api<any[]>("/api/jobs"), api<any[]>("/api/resumes")])
      .then(([jobRows, resumeRows]) => {
        setJobs(jobRows);
        setResumes(resumeRows);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function createJob() {
    if (!form.jd_text.trim() || !form.title.trim()) {
      setError("请填写岗位名称和 JD 文本");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const job = await api<any>("/api/jobs", { method: "POST", body: JSON.stringify(form) });
      setInfo(`职位 ${job.id} 已创建`);
      load();
    } catch (e: any) {
      setError(e.message || "创建失败");
    } finally {
      setBusy(false);
    }
  }

  async function match(jobId: number) {
    if (!resumeId) {
      setError("请先选择简历");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<any>(`/api/jobs/${jobId}/match`, {
        method: "POST",
        body: JSON.stringify({ resume_id: resumeId }),
      });
      setInfo(`匹配分：${result.match_score}`);
      load();
    } catch (e: any) {
      setError(e.message || "匹配失败");
    } finally {
      setBusy(false);
    }
  }

  async function createPacket(jobId: number) {
    if (!resumeId) {
      setError("请先选择简历");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const result = await api<any>(`/api/jobs/${jobId}/packet`, {
        method: "POST",
        body: JSON.stringify({ resume_id: resumeId, allow_llm: allowLlm }),
      });
      setInfo(`投递包已生成，投递项 #${result.application_id}`);
    } catch (e: any) {
      setError(e.message || "生成投递包失败");
    } finally {
      setBusy(false);
    }
  }

  async function searchJobs() {
    if (!searchKeyword.trim()) {
      setSearchError("请输入搜索关键词");
      return;
    }
    setSearching(true);
    setSearchError("");
    setError("");
    setSearchResults([]);
    setSelectedUrls([]);
    try {
      const result = await api<any>("/api/jobs/search", {
        method: "POST",
        body: JSON.stringify({ platform: "boss", keyword: searchKeyword, city: searchCity }),
      });
      setSearchResults(result.items || []);
      if (!result.items?.length) {
        setSearchError("没有抓取到岗位，BOSS 可能要求登录或验证，请检查平台账号配置");
      }
    } catch (e: any) {
      setSearchError(e.message || "搜索失败");
    } finally {
      setSearching(false);
    }
  }

  function toggleResult(url: string) {
    setSelectedUrls((prev) => (prev.includes(url) ? prev.filter((u) => u !== url) : [...prev, url]));
  }

  async function importSelected() {
    if (!selectedUrls.length) {
      setSearchError("请先勾选要导入的职位");
      return;
    }
    setBusy(true);
    setSearchError("");
    setError("");
    setInfo("");
    try {
      const items = searchResults
        .filter((r) => selectedUrls.includes(r.url))
        .map((r) => ({ platform: "boss", company: r.company || "", title: r.title, url: r.url }));
      const result = await api<any>("/api/jobs/import", {
        method: "POST",
        body: JSON.stringify({ items }),
      });
      setInfo(`已导入 ${result.created.length} 个职位，跳过 ${result.skipped} 个`);
      setSearchResults([]);
      setSelectedUrls([]);
      load();
    } catch (e: any) {
      setError(e.message || "导入失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Nav />
      <main className="main">
        <div className="page-header">
          <h1>职位与 JD</h1>
        </div>
        <div className="panel">
          <div className="row">
            <select value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
              <option value="manual">手动</option>
              <option value="boss">Boss直聘</option>
              <option value="liepin">猎聘</option>
              <option value="zhilian">智联招聘</option>
              <option value="job51">前程无忧</option>
            </select>
            <input placeholder="公司" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
            <input placeholder="岗位（必填）" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input placeholder="URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          </div>
          <textarea placeholder="粘贴 JD 文本（必填）" value={form.jd_text} onChange={(e) => setForm({ ...form, jd_text: e.target.value })} />
          <div className="action-bar">
            <button className="primary" disabled={busy || !form.title.trim() || !form.jd_text.trim()} onClick={createJob}>
              添加职位
            </button>
          </div>
        </div>
        <div className="panel">
          <select value={resumeId} onChange={(e) => setResumeId(Number(e.target.value))}>
            <option value={0}>选择简历</option>
            {resumes.map((r) => <option key={r.id} value={r.id}>{r.filename}</option>)}
          </select>
          <label className="consent">
            <input type="checkbox" checked={allowLlm} onChange={(e) => setAllowLlm(e.target.checked)} />
            允许将简历内容发送至云端 AI（用于生成打招呼语）
          </label>
        </div>
        <div className="panel">
          <div className="item-header">
            <strong>职位搜索采集</strong>
          </div>
          <div className="row">
            <input placeholder="关键词（必填）" value={searchKeyword} onChange={(e) => setSearchKeyword(e.target.value)} />
            <input placeholder="城市（可留空，如：深圳）" value={searchCity} onChange={(e) => setSearchCity(e.target.value)} />
            <button className="primary" disabled={busy || searching} onClick={searchJobs}>
              {searching ? "搜索中..." : "搜索职位"}
            </button>
          </div>
          {searching && <div className="loading">正在打开 BOSS 搜索页抓取岗位...</div>}
          {searchResults.length > 0 && (
            <>
              {searchResults.map((r) => (
                <label className="item" key={r.url}>
                  <div className="item-header">
                    <input type="checkbox" checked={selectedUrls.includes(r.url)} onChange={() => toggleResult(r.url)} />
                    <strong>{r.title}</strong>
                    <span className="muted">{r.company || "未知公司"} {r.salary || ""}</span>
                  </div>
                  <div className="action-bar">
                    <a href={r.url} target="_blank" rel="noreferrer">查看岗位</a>
                  </div>
                </label>
              ))}
              <div className="action-bar">
                <button className="primary" disabled={busy || !selectedUrls.length} onClick={importSelected}>
                  导入选中职位（{selectedUrls.length}）
                </button>
              </div>
            </>
          )}
        </div>
        {error && <div className="error-box">{error}</div>}
        {searchError && <div className="error-box">{searchError}</div>}
        {info && <div className="banner">{info}</div>}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : jobs.length === 0 ? (
          <div className="empty">还没有职位，请先添加一条 JD。</div>
        ) : (
          jobs.map((j) => (
            <div className="item" key={j.id}>
              <div className="item-header">
                <strong>{j.company || "未命名公司"} - {j.title}</strong>
                <span className="muted">匹配分：{j.match_score ?? "-"}</span>
              </div>
              <div className="action-bar">
                <button className="btn-secondary" disabled={busy || !resumeId} onClick={() => match(j.id)}>计算匹配分</button>
                <button className="primary" disabled={busy || !resumeId} onClick={() => createPacket(j.id)}>生成投递包</button>
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
