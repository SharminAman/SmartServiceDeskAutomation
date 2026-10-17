import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Policy, RuleDraft, TemplateDraft } from "../types";

const SPECIALS = ["missing_fields", "completed", "uncategorised", "mismatch", "default"];
const SPECIAL_LABELS: Record<string, string> = {
  missing_fields: "Missing information",
  completed: "Already completed",
  uncategorised: "No rule matched",
  mismatch: "Category differs",
  default: "Fallback",
};

export function Admin() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [tab, setTab] = useState<"rules" | "templates" | "review" | "lists">("rules");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [keyword, setKeyword] = useState<Record<number, string>>({});

  useEffect(() => {
    api<Policy>("/api/admin/policy")
      .then(setPolicy)
      .catch((err: Error) => setError(err.message));
  }, []);

  async function save(path: string, body: unknown, message: string) {
    setBusy(true);
    setError("");
    try {
      const next = await api<Policy>(path, { method: "PUT", body: JSON.stringify(body) });
      setPolicy(next);
      setNotice(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The change was not saved");
    } finally {
      setBusy(false);
    }
  }

  if (!policy) {
    return <div className="page">{error ? <p className="banner error">{error}</p> : "Loading rules…"}</div>;
  }

  const specials = policy.templates.filter((item) => SPECIALS.includes(item.template_key));
  const categoryTemplates = policy.templates.filter((item) => !SPECIALS.includes(item.template_key));

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="kicker">Admin</div>
          <h1>Rules you can change.</h1>
        </div>
      </header>
      {notice ? (
        <p className="banner">
          {notice} <Link to="/requests">Re-run analysis</Link> so existing requests pick this up.
        </p>
      ) : null}
      {error ? <p className="banner error">{error}</p> : null}
      <div className="tabs">
        {(
          [
            ["rules", "Rules"],
            ["templates", "Acknowledgements"],
            ["review", "Review"],
            ["lists", "Allowed values"],
          ] as const
        ).map(([id, label]) => (
          <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "rules" ? (
        <section className="panel">
          <p className="hint">First matching keyword wins. Order is the order on this page.</p>
          {policy.rules.map((rule, index) => (
            <article className="rule-card" key={index}>
              <div className="grid-2">
                <label className="field">
                  <span>Category {index + 1}</span>
                  <input
                    value={rule.category}
                    onChange={(event) => updateRule(policy, setPolicy, index, { ...rule, category: event.target.value })}
                  />
                </label>
                <div className="actions" style={{ alignItems: "end" }}>
                  <button type="button" className="btn small" onClick={() => move(policy, setPolicy, index, -1)} disabled={index === 0}>
                    Up
                  </button>
                  <button
                    type="button"
                    className="btn small"
                    onClick={() => move(policy, setPolicy, index, 1)}
                    disabled={index === policy.rules.length - 1}
                  >
                    Down
                  </button>
                  <button type="button" className="btn small" onClick={() => toggleRule(policy, setPolicy, index)}>
                    {rule.enabled ? "Enabled" : "Off"}
                  </button>
                  <button type="button" className="btn small danger" onClick={() => removeRule(policy, setPolicy, index)}>
                    Remove
                  </button>
                </div>
              </div>
              <div className="chips">
                {rule.keywords.map((item) => (
                  <button key={item} type="button" onClick={() => dropKeyword(policy, setPolicy, index, item)}>
                    {item} ×
                  </button>
                ))}
              </div>
              <form
                className="toolbar"
                onSubmit={(event) => {
                  event.preventDefault();
                  const value = (keyword[index] || "").trim();
                  if (!value) return;
                  updateRule(policy, setPolicy, index, { ...rule, keywords: [...rule.keywords, value] });
                  setKeyword({ ...keyword, [index]: "" });
                }}
              >
                <label className="search">
                  <input
                    value={keyword[index] || ""}
                    placeholder="Add a keyword"
                    onChange={(event) => setKeyword({ ...keyword, [index]: event.target.value })}
                  />
                </label>
                <button className="btn small">Add keyword</button>
              </form>
            </article>
          ))}
          <div className="actions">
            <button
              className="btn"
              onClick={() =>
                setPolicy({ ...policy, rules: [...policy.rules, { category: "", enabled: true, keywords: [] }] })
              }
            >
              Add a rule
            </button>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() => save("/api/admin/rules", { rules: policy.rules }, "Rules saved.")}
            >
              Save rules
            </button>
          </div>
        </section>
      ) : null}

      {tab === "templates" ? (
        <section className="panel">
          <p className="hint">
            Placeholders: {"{request_id}"} {"{category}"} {"{request_type}"} {"{priority}"} {"{status}"} {"{missing_fields}"}
          </p>
          <h2>Shared sentences</h2>
          {specials.map((item) => (
            <TemplateEditor key={item.template_key} item={item} policy={policy} setPolicy={setPolicy} />
          ))}
          <h2>Category sentences</h2>
          {categoryTemplates.map((item) => (
            <TemplateEditor key={item.template_key} item={item} policy={policy} setPolicy={setPolicy} />
          ))}
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => save("/api/admin/templates", { templates: policy.templates }, "Acknowledgements saved.")}
          >
            Save acknowledgements
          </button>
        </section>
      ) : null}

      {tab === "review" ? (
        <section className="panel">
          <Switch
            label="Missing or invalid fields"
            checked={policy.settings.flag_missing_fields}
            onChange={(checked) => setPolicy({ ...policy, settings: { ...policy.settings, flag_missing_fields: checked } })}
          />
          <Switch
            label="Category does not match, or no rule matches"
            checked={policy.settings.flag_category_mismatch}
            onChange={(checked) =>
              setPolicy({ ...policy, settings: { ...policy.settings, flag_category_mismatch: checked } })
            }
          />
          <Switch
            label="High priority"
            checked={policy.settings.flag_high_priority}
            onChange={(checked) => setPolicy({ ...policy, settings: { ...policy.settings, flag_high_priority: checked } })}
          />
          <Switch
            label="Status is Completed"
            checked={policy.settings.flag_completed}
            onChange={(checked) => setPolicy({ ...policy, settings: { ...policy.settings, flag_completed: checked } })}
          />
          <label className="field" style={{ marginTop: 16 }}>
            <span>Summary minimum length</span>
            <input
              type="number"
              min={0}
              max={500}
              value={policy.settings.summary_min_length}
              onChange={(event) =>
                setPolicy({
                  ...policy,
                  settings: { ...policy.settings, summary_min_length: Number(event.target.value) },
                })
              }
            />
          </label>
          <PhraseEditor
            label="Sensitive phrases"
            values={policy.settings.sensitive_keywords}
            onChange={(sensitive_keywords) => setPolicy({ ...policy, settings: { ...policy.settings, sensitive_keywords } })}
          />
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => save("/api/admin/settings", policy.settings, "Review settings saved.")}
          >
            Save review settings
          </button>
        </section>
      ) : null}

      {tab === "lists" ? (
        <section className="panel">
          <div className="grid-2">
            <PhraseEditor
              label="Priorities"
              values={policy.lists.priorities}
              onChange={(priorities) => setPolicy({ ...policy, lists: { ...policy.lists, priorities } })}
            />
            <PhraseEditor
              label="Channels"
              values={policy.lists.channels}
              onChange={(channels) => setPolicy({ ...policy, lists: { ...policy.lists, channels } })}
            />
            <PhraseEditor
              label="Statuses"
              values={policy.lists.statuses}
              onChange={(statuses) => setPolicy({ ...policy, lists: { ...policy.lists, statuses } })}
            />
            <PhraseEditor
              label="Request types"
              values={policy.lists.request_types}
              onChange={(request_types) => setPolicy({ ...policy, lists: { ...policy.lists, request_types } })}
            />
          </div>
          <button className="btn primary" disabled={busy} onClick={() => save("/api/admin/lists", policy.lists, "Allowed values saved.")}>
            Save allowed values
          </button>
        </section>
      ) : null}
    </div>
  );
}

function TemplateEditor({
  item,
  policy,
  setPolicy,
}: {
  item: TemplateDraft;
  policy: Policy;
  setPolicy: (policy: Policy) => void;
}) {
  return (
    <label className="field">
      <span>{SPECIAL_LABELS[item.template_key] || item.template_key}</span>
      <textarea
        value={item.body}
        onChange={(event) =>
          setPolicy({
            ...policy,
            templates: policy.templates.map((row) =>
              row.template_key === item.template_key ? { ...row, body: event.target.value } : row,
            ),
          })
        }
      />
    </label>
  );
}

function Switch({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <div className="switch">
      <span>{label}</span>
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}>
        <i />
      </button>
    </div>
  );
}

function PhraseEditor({ label, values, onChange }: { label: string; values: string[]; onChange: (values: string[]) => void }) {
  const [draft, setDraft] = useState("");
  function add(event: FormEvent) {
    event.preventDefault();
    const next = draft.trim();
    if (!next) return;
    onChange([...values, next]);
    setDraft("");
  }
  return (
    <div>
      <div className="kicker" style={{ marginTop: 12 }}>
        {label}
      </div>
      <div className="chips">
        {values.map((item) => (
          <button key={item} type="button" onClick={() => onChange(values.filter((value) => value !== item))}>
            {item} ×
          </button>
        ))}
      </div>
      <form className="toolbar" onSubmit={add}>
        <label className="search">
          <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={`Add a ${label.toLowerCase()}`} />
        </label>
        <button className="btn small">Add</button>
      </form>
    </div>
  );
}

function updateRule(policy: Policy, setPolicy: (policy: Policy) => void, index: number, rule: RuleDraft) {
  const rules = policy.rules.slice();
  rules[index] = rule;
  setPolicy({ ...policy, rules });
}

function move(policy: Policy, setPolicy: (policy: Policy) => void, index: number, direction: number) {
  const rules = policy.rules.slice();
  const target = index + direction;
  const current = rules[index];
  const other = rules[target];
  if (!current || !other) return;
  rules[index] = other;
  rules[target] = current;
  setPolicy({ ...policy, rules });
}

function toggleRule(policy: Policy, setPolicy: (policy: Policy) => void, index: number) {
  const rule = policy.rules[index];
  if (!rule) return;
  updateRule(policy, setPolicy, index, { ...rule, enabled: !rule.enabled });
}

function removeRule(policy: Policy, setPolicy: (policy: Policy) => void, index: number) {
  setPolicy({ ...policy, rules: policy.rules.filter((_, item) => item !== index) });
}

function dropKeyword(policy: Policy, setPolicy: (policy: Policy) => void, index: number, keyword: string) {
  const rule = policy.rules[index];
  if (!rule) return;
  updateRule(policy, setPolicy, index, { ...rule, keywords: rule.keywords.filter((item) => item !== keyword) });
}
