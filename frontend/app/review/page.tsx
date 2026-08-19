"use client";

import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../../lib/api";

export default function ReviewPage() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [resumeId, setResumeId] = useState(0);
  const [jobId, setJobId] = useState(0);
  const [review, setReview] = useState("");
  const [error, setError] = useState("");
  const [allowLlm, setAllowLlm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api<any[]>("/api/resumes"), api<any[]>("/api/jobs")])
      .then(([r, j]) => {
        setResumes(r);
        setJobs(j);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function run() {
    if (!resumeId) {
      setError("请选择简历");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const query = [`allow_llm=${allowLlm ? 1 : 0}`];
      if (jobId) query.push(`job_id=${jobId}`);
      const url = `/api/reviews/resumes/${resumeId}?${query.join("&")}`;
      const result = await api<any>(url, { method: "POST" });
      setReview(result.review);
    } catch (e: any) {
      setError(e.message || "审查失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Nav />
      <main className="main">
        <div className="page-header">
          <h1>AI 简历审查</h1>
        </div>
        <div className="panel">
          <div className="row">
            <select value={resumeId} onChange={(e) => setResumeId(Number(e.target.value))}>
              <option value={0}>选择简历</option>
              {resumes.map((r) => <option key={r.id} value={r.id}>{r.filename}</option>)}
            </select>
            <select value={jobId} onChange={(e) => setJobId(Number(e.target.value))}>
              <option value={0}>不指定 JD</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.company} - {j.title}</option>)}
            </select>
            <button className="primary" disabled={busy || !resumeId} onClick={run}>
              {busy ? "审查中..." : "开始审查"}
            </button>
          </div>
          <label className="consent">
            <input type="checkbox" checked={allowLlm} onChange={(e) => setAllowLlm(e.target.checked)} />
            允许将简历内容发送至云端 AI（用于生成审查建议）
          </label>
        </div>
        {loading ? (
          <div className="loading">加载中...</div>
        ) : resumes.length === 0 ? (
          <div className="empty">请先上传简历。</div>
        ) : null}
        {error && <div className="error-box">{error}</div>}
        {review && <div className="panel"><pre>{review}</pre></div>}
      </main>
    </div>
  );
}
