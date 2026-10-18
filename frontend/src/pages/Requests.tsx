import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, downloadCsv } from "../api";
import type { Meta, RequestItem, RequestList, UploadResult } from "../types";

const emptyForm = {
  request_id: "",
  submitted_date: "",
  requester_role: "",
  request_type: "",
  request_summary: "",
  priority: "",
  channel: "",
  status: "New",
};

export function Requests() {
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState<RequestList | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState(params.get("q") || "");
  const [selected, setSelected] = useState<RequestItem | null>(null);
  const [creating, setCreating] = useState(params.get("new") === "1");
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);

  const queryKey = params.toString();

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const next = new URLSearchParams(params);
      if (query) next.set("q", query);
      else next.delete("q");
      if (next.toString() !== params.toString()) setParams(next, { replace: true });
    }, 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  function load() {
    const search = new URLSearchParams(params);
    search.delete("open");
    search.delete("new");
    api<RequestList>(`/api/requests?${search.toString()}`)
      .then((data) => {
        setList(data);
        const open = params.get("open");
        if (open) {
          const match = data.items.find((item) => String(item.id) === open);
          if (match) setSelected(match);
        }
      })
      .catch((err: Error) => setError(err.message));
  }

  useEffect(() => {
    load();
    api<Meta>("/api/meta")
      .then((data) => {
        setMeta(data);
        setForm((current) => ({ ...current, request_id: current.request_id || data.next_id }));
      })
      .catch(() => undefined);
  }, [queryKey]);

  function toggle(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (next.get(key) === value) next.delete(key);
    else next.set(key, value);
    setParams(next);
  }

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  async function saveRequest(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api<RequestItem>("/api/requests", { method: "POST", body: JSON.stringify(form) });
      setCreating(false);
      setNotice(`${created.request_id} is on the desk.`);
      setSelected(created);
      setForm({ ...emptyForm, request_id: "" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The request was not saved");
    } finally {
      setBusy(false);
    }
  }

  async function remove(item: RequestItem) {
    if (!window.confirm(`Remove ${item.request_id} from the desk?`)) return;
    await api(`/api/requests/${item.id}`, { method: "DELETE" });
    setSelected(null);
    setNotice(`${item.request_id} was removed.`);
    load();
  }

  async function reanalyse() {
    setBusy(true);
    try {
      const result = await api<{ updated: number }>("/api/requests/reanalyse", { method: "POST" });
      setNotice(`${result.updated} requests analysed again with the current rules.`);
      setSelected(null);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis did not finish");
    } finally {
      setBusy(false);
    }
  }

  const facets = list?.facets;
  const filters = useMemo(
    () => [
      ["review", "yes", "Needs a person"],
      ["review", "no", "Clear"],
      ["missing", "yes", "Missing information"],
      ["match", "no", "Category differs"],
      ["match", "yes", "Category agrees"],
    ] as const,
    [],
  );

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="kicker">{list ? `${list.total} showing` : "Requests"}</div>
          <h1>Request table</h1>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => downloadCsv("view", params)}>
            Download view
          </button>
          <button className="btn" onClick={() => downloadCsv("all")}>
            Download all
          </button>
          <button className="btn" onClick={reanalyse} disabled={busy}>
            Re-run analysis
          </button>
          <button className="btn" onClick={() => setUploading(true)}>
            Upload CSV
          </button>
          <button className="btn primary" onClick={() => setCreating(true)}>
            New request
          </button>
        </div>
      </header>

      {notice ? <p className="banner">{notice}</p> : null}
      {error ? <p className="banner error">{error}</p> : null}

      <div className="toolbar">
        <label className="search">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search id, role, summary, or category"
            aria-label="Search requests"
          />
        </label>
      </div>
      <div className="pills">
        {filters.map(([key, value, label]) => (
          <button key={label} className={params.get(key) === value ? "on" : ""} onClick={() => toggle(key, value)}>
            {label}
          </button>
        ))}
      </div>
      <div className="filters">
        <select value={params.get("category") || ""} onChange={(event) => setFilter("category", event.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {facets?.categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select value={params.get("priority") || ""} onChange={(event) => setFilter("priority", event.target.value)} aria-label="Priority">
          <option value="">All priorities</option>
          {facets?.priorities.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select value={params.get("status") || ""} onChange={(event) => setFilter("status", event.target.value)} aria-label="Status">
          <option value="">All statuses</option>
          {facets?.statuses.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select value={params.get("channel") || ""} onChange={(event) => setFilter("channel", event.target.value)} aria-label="Channel">
          <option value="">All channels</option>
          {facets?.channels.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </div>

      <div className="table-wrap">
        {!list ? <p className="empty">Loading requests…</p> : null}
        {list && list.items.length === 0 ? (
          <div className="empty">
            <h2>The table is empty.</h2>
            <p>Add a request, or upload the sample spreadsheet.</p>
          </div>
        ) : null}
        {list && list.items.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Request</th>
                <th>Human intervention needed?</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((item) => (
                <tr
                  key={item.id}
                  className={selected?.id === item.id ? "clickable selected" : "clickable"}
                  onClick={() => setSelected(item)}
                >
                  <td>
                    <button className="id-btn" onClick={() => setSelected(item)}>
                      {item.request_id}
                    </button>
                    <div className="sub">{item.submitted_date}</div>
                  </td>
                  <td>
                    <span className={item.needs_human_review ? "pill warn" : "pill good"}>
                      {item.needs_human_review ? "Yes" : "No"}
                    </span>
                  </td>
                  <td>
                    {item.category}
                    <div className="sub">{item.category_agrees ? `via ${item.rule_matched}` : "Check this category"}</div>
                  </td>
                  <td>{item.priority || "—"}</td>
                  <td>
                    {item.requester_role || "—"}
                    <div className="sub">{item.request_summary.slice(0, 80)}</div>
                  </td>
                  <td>{item.status || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>

      {selected ? (
        <div className="backdrop" onClick={() => setSelected(null)}>
          <aside
            className={selected.needs_human_review ? "verdict verdict-alert" : "verdict verdict-clear"}
            onClick={(event) => event.stopPropagation()}
          >
            <header className="verdict-banner">
              <div className="verdict-meta">
                <span>{selected.request_id}</span>
                <span>
                  {selected.needs_human_review
                    ? `${selected.review_reasons.length} ${selected.review_reasons.length === 1 ? "reason" : "reasons"}`
                    : "No review flag"}
                </span>
              </div>
              <button className="btn small verdict-close" onClick={() => setSelected(null)}>
                Close
              </button>
              <h2>{selected.needs_human_review ? "A person must see this" : "No person is needed"}</h2>
            </header>

            <section className="why-panel" aria-label="Why human intervention is needed">
              <h3>Why human intervention is needed</h3>
              {selected.review_reasons.length > 0 ? (
                <ol className="why-list">
                  {selected.review_reasons.map((reason, index) => (
                    <li key={reason}>
                      <span>{index + 1}</span>
                      <p>{reason}</p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="why-clear">
                  No human intervention is needed. Nothing in this request triggered a review rule.
                </p>
              )}
            </section>

            <div className="verdict-rest">
              <div className="ack">
                <span>Suggested acknowledgement</span>
                {selected.acknowledgement}
              </div>
              <p className="case-summary">{selected.request_summary || "No summary was provided."}</p>
              <div className="facts">
                <div>
                  <span>Submitted</span>
                  {selected.submitted_date || "—"}
                </div>
                <div>
                  <span>Role</span>
                  {selected.requester_role || "—"}
                </div>
                <div>
                  <span>Request type</span>
                  {selected.request_type || "—"}
                </div>
                <div>
                  <span>Category</span>
                  {selected.category}
                </div>
                <div>
                  <span>Rule</span>
                  {selected.rule_matched || "No keyword matched"}
                </div>
                <div>
                  <span>Priority</span>
                  {selected.priority || "—"}
                </div>
                <div>
                  <span>Channel</span>
                  {selected.channel || "—"}
                </div>
                <div>
                  <span>Status</span>
                  {selected.status || "—"}
                </div>
              </div>
              {selected.missing_fields.length > 0 ? (
                <p>Missing or invalid: {selected.missing_fields.join(", ")}</p>
              ) : null}
              <button className="btn danger" onClick={() => remove(selected)}>
                Remove request
              </button>
            </div>
          </aside>
        </div>
      ) : null}

      {creating ? (
        <div className="backdrop" onClick={() => setCreating(false)}>
          <form className="modal" onClick={(event) => event.stopPropagation()} onSubmit={saveRequest}>
            <div className="kicker">New row</div>
            <h2>Add a request</h2>
            <p className="hint">Blank fields are saved and flagged. The request ID is the one required piece.</p>
            <div className="grid-2">
              <label className="field">
                <span>Request ID</span>
                <input value={form.request_id} onChange={(event) => setForm({ ...form, request_id: event.target.value })} />
              </label>
              <label className="field">
                <span>Submitted date</span>
                <input
                  placeholder="DD/MM/YYYY"
                  value={form.submitted_date}
                  onChange={(event) => setForm({ ...form, submitted_date: event.target.value })}
                />
              </label>
              <label className="field">
                <span>Requester role</span>
                <input value={form.requester_role} onChange={(event) => setForm({ ...form, requester_role: event.target.value })} />
              </label>
              <label className="field">
                <span>Request type</span>
                <select value={form.request_type} onChange={(event) => setForm({ ...form, request_type: event.target.value })}>
                  <option value="">Select</option>
                  {meta?.request_types.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Priority</span>
                <select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}>
                  <option value="">Select</option>
                  {meta?.priorities.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Channel</span>
                <select value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value })}>
                  <option value="">Select</option>
                  {meta?.channels.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Status</span>
                <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                  <option value="">Select</option>
                  {meta?.statuses.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>Summary</span>
              <textarea value={form.request_summary} onChange={(event) => setForm({ ...form, request_summary: event.target.value })} />
            </label>
            <div className="actions">
              <button type="button" className="btn" onClick={() => setCreating(false)}>
                Cancel
              </button>
              <button className="btn primary" disabled={busy}>
                {busy ? "Saving…" : "Save and analyse"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {uploading ? (
        <UploadModal
          onClose={() => setUploading(false)}
          onDone={(result) => {
            setUploading(false);
            const failed = result.failed.length ? ` ${result.failed.length} row(s) skipped.` : "";
            setNotice(`Added ${result.inserted}, updated ${result.updated}.${failed}`);
            load();
          }}
        />
      ) : null}
    </div>
  );
}

function UploadModal({ onClose, onDone }: { onClose: () => void; onDone: (result: UploadResult) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<UploadResult>("/api/requests/upload", { method: "POST", body });
      onDone(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="backdrop" onClick={onClose}>
      <form className="modal" onClick={(event) => event.stopPropagation()} onSubmit={submit}>
        <div className="kicker">Spreadsheet</div>
        <h2>Upload requests</h2>
        <p className="hint">
          New request IDs are added. An ID that is already on the desk is updated and analysed again. A downloaded
          file can be uploaded straight back.
        </p>
        <label
          className={over ? "drop over" : "drop"}
          onDragOver={(event) => {
            event.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setOver(false);
            const dropped = event.dataTransfer.files[0];
            if (dropped) setFile(dropped);
          }}
        >
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          {file ? file.name : "Drop a CSV here, or click to choose one"}
        </label>
        {error ? <p className="banner error">{error}</p> : null}
        <div className="actions" style={{ marginTop: 16 }}>
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!file || busy}>
            {busy ? "Reading…" : "Upload and analyse"}
          </button>
        </div>
      </form>
    </div>
  );
}
