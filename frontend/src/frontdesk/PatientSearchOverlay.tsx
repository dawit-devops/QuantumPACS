import React, { useCallback, useEffect, useState } from "react";
import {
  App,
  Button,
  Input,
  List,
  Modal,
  Tag,
  Tooltip,
} from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import {
  searchRisPatients,
  type FrontDeskPatient,
  type PatientSearchQuery,
} from "../api/frontdesk";
import "./FrontDesk.css";

const RECENTS_KEY = "fd.patient-search.recents";
const OPEN_EVENT = "fd.patient-search.open";

function loadRecents(): string[] {
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 5) : [];
  } catch {
    return [];
  }
}

function saveRecents(term: string) {
  try {
    const next = [term, ...loadRecents().filter((r) => r !== term)].slice(0, 5);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {
    // localStorage unavailable (private mode) — recents are best-effort.
  }
}

// FD-07: global patient quick search. Searches by name/MRN, DOB, or phone;
// remembers recent terms; clicking a result opens the patient detail page.
function PatientSearchOverlay() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [dob, setDob] = useState("");
  const [phone, setPhone] = useState("");
  const [results, setResults] = useState<FrontDeskPatient[]>([]);
  const [recents, setRecents] = useState<string[]>(loadRecents);
  const [searching, setSearching] = useState(false);

  const runSearch = useCallback(() => {
    const query: PatientSearchQuery = {};
    if (q.trim()) query.q = q.trim();
    if (dob.trim()) query.dob = dob.trim();
    if (phone.trim()) query.phone = phone.trim();
    if (q.trim().length >= 2 || dob.trim() || phone.trim()) {
      setSearching(true);
      searchRisPatients(query)
        .then((rows) => setResults(rows))
        .catch((e: any) => message.error(e.message || "Search failed"))
        .finally(() => setSearching(false));
    } else {
      setResults([]);
    }
  }, [q, dob, phone, message]);

  useEffect(() => {
    if (open) runSearch();
  }, [open, runSearch]);

  // The Sidebar "Patient Search" item broadcasts a custom event to open the
  // overlay — the trigger and the nav item stay in sync.
  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener(OPEN_EVENT, handler);
    return () => window.removeEventListener(OPEN_EVENT, handler);
  }, []);

  const openPatient = useCallback(
    (patient: FrontDeskPatient) => {
      const term = q.trim() || patient.name || patient.patient_id;
      if (term) saveRecents(term);
      setRecents(loadRecents());
      setOpen(false);
      navigate(`/patients/${patient.patient_id}`);
    },
    [navigate, q],
  );

  const useRecent = (term: string) => {
    // Re-run the name search with the recent term.
    setQ(term);
    setDob("");
    setPhone("");
  };

  return (
    <>
      <Tooltip title="Search patients">
        <Button
          className="fd-global-search"
          icon={<SearchOutlined />}
          aria-label="Patient search"
          onClick={() => setOpen(true)}
        />
      </Tooltip>
      <Modal
        title="Patient Search"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={560}
      >
        <div className="fd-search-fields">
          <Input
            placeholder="Search patients by name or MRN"
            aria-label="Search patients"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            allowClear
            onPressEnter={runSearch}
          />
          <Input
            placeholder="DOB (e.g. 1980)"
            aria-label="Search by DOB"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
            allowClear
            onPressEnter={runSearch}
          />
          <Input
            placeholder="Phone"
            aria-label="Search by phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            allowClear
            onPressEnter={runSearch}
          />
        </div>

        {recents.length > 0 && !q && !dob && !phone && (
          <div className="fd-search-recents">
            <div className="fd-search-recents-label">Recent searches</div>
            <div className="fd-search-recents-tags">
              {recents.map((r) => (
                <Tag
                  key={r}
                  style={{ cursor: "pointer" }}
                  onClick={() => useRecent(r)}
                >
                  {r}
                </Tag>
              ))}
            </div>
          </div>
        )}

        <List
          loading={searching}
          dataSource={results}
          locale={{ emptyText: "No patients match" }}
          renderItem={(p) => (
            <List.Item
              className="fd-patient-result"
              onClick={() => openPatient(p)}
              style={{ cursor: "pointer" }}
            >
              <List.Item.Meta
                title={p.name}
                description={
                  <span className="fd-patient-meta">
                    {p.patient_id || "—"} · {p.birth_date || "—"}
                    {p.phone ? ` · ${p.phone}` : ""}
                  </span>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </>
  );
}

export default PatientSearchOverlay;
