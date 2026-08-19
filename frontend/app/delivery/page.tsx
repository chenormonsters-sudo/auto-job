"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../../lib/api";

export default function DeliveryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [rate, setRate] = useState(20);
  const [fingerprint, setFingerprint] = useState(false);

  const load = useCallback(() => {
    Promise.all([api<any>("/api/health"), api<any[]>("/api/applications")])
      .then(([health, rows]) => {
        setRate(health.min_delivery_interval_seconds);
        setFingerprint(health.fingerprint_spoofing_enabled);
        setItems(rows);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  function toggle(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function confirmSelection() {
    if (!selected.length) {
      setError("请先勾选投递项");
      return;
    }
    setBusy(true);
    try {
      await api("/api/applications/select", {
        method: "POST",
        body: JSON.stringify({ application_ids: selected, confirmed: true }),
      });
      setInfo(`已确认 ${selected.length} 项`);
      load();
    } catch (e: any) {
      setError(e.message || "确认失败");
    } finally {
      setBusy(false);
    }
  }

  async function dryRun() {
    if (!selected.length) {
      setError("请先勾选投递项");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<any>("/api/deliveries/dry-run", {
        method: "POST",
        body: JSON.stringify({ application_ids: selected }),
      });
      setInfo(JSON.stringify(result.results, null, 2));
    } catch (e: any) {
      setError(e.message || "试运行失败");
    } finally {
      setBusy(false);
    }
  }

  async function realDelivery() {
    setBusy(true);
    setError("");
    try {
      const result = await api<any>("/api/deliveries/confirm", {
        method: "POST",
        body: JSON.stringify({ application_ids: selected }),
      });
      setInfo(JSON.stringify(result.results, null, 2));
      load();
    } catch (e: any) {
      setError(e.message || "投递失败");
    } finally {
      setBusy(false);
      setShowConfirm(false);
    }
  }

  async function toggleFingerprint() {
    setBusy(true);
    setError("");
    try {
      const result = await api<any>("/api/settings/fingerprint", {
        method: "POST",
        body: JSON.stringify({ enabled: !fingerprint }),
      });
      setFingerprint(result.fingerprint_spoofing_enabled);
    } catch (e: any) {
      setError(e.message || "指纹伪装设置失败");
    } finally {
      setBusy(false);
    }
  }

  function exportCsv() {
    const header = ["id", "job_id", "resume_id", "status", "greeting"];
    const rows = items.map((item) => [item.id, item.job_id, item.resume_id, item.status, `"${item.greeting.replaceAll('"', '""')}"`]);
    const csv = [header.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "delivery-records.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <Nav />
      <main className="main">
        <div className="page-header">
          <h1>投递确认队列</h1>
          <span className="rate">最小投递间隔：{rate} 秒/条</span>
        </div>
        <div className="banner danger">
          自动化投递存在账号受限风险。系统只做浏览器页面交互，试运行不会真实发送；真实投递需要二次确认。
          {fingerprint ? " 指纹伪装已开启，但无法 100% 规避风控。" : " 指纹伪装当前关闭。"}
          <button className="btn-secondary" disabled={busy} onClick={toggleFingerprint}>
            {fingerprint ? "关闭指纹伪装" : "开启指纹伪装"}
          </button>
        </div>
        {error && <div className="error-box">{error}</div>}
        {info && <div className="panel"><pre>{info}</pre></div>}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : items.length === 0 ? (
          <div className="empty">还没有投递项，请先在职位页生成投递包。</div>
        ) : (
          items.map((item) => (
            <label className="item" key={item.id}>
              <div className="item-header">
                <input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} />
                <strong>投递项 #{item.id}</strong>
                <span className={`status ${item.status}`}>{item.status}</span>
              </div>
              <pre>{item.greeting}</pre>
            </label>
          ))
        )}
        <div className="action-bar">
          <button className="primary" disabled={busy || !selected.length} onClick={confirmSelection}>
            确认选中项（{selected.length}）
          </button>
          <button className="btn-secondary" disabled={busy || !selected.length} onClick={dryRun}>
            试运行
          </button>
          <button className="btn-danger" disabled={busy || !selected.length} onClick={() => setShowConfirm(true)}>
            真实投递
          </button>
          <button className="btn-secondary" disabled={!items.length} onClick={exportCsv}>
            导出 CSV
          </button>
        </div>
      </main>
      {showConfirm && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>确认真实投递？</h3>
            <p>将真实投递 {selected.length} 个已勾选项，此操作不可撤销，且受平台风控影响。</p>
            <div className="action-bar">
              <button className="btn-danger" disabled={busy} onClick={realDelivery}>确认投递</button>
              <button className="btn-secondary" disabled={busy} onClick={() => setShowConfirm(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
