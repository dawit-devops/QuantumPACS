import React from "react";
import { useAuth } from "../auth/AuthContext";
import "./report.css";

const { Text } = (() => {
  // Keep antd Typography out of the render path: the report document is
  // plain HTML styled by report.css (design-system REPORT-TEMPLATE.html).
  return { Text: null };
})();

interface ReportDocumentProps {
  /** Tenant/issuing facility shown in the masthead co-brand block. */
  tenantName?: string;
  /** Exam / report metadata for the key-value table. */
  meta?: {
    patient_name?: string;
    patient_id?: string;
    patient_birth_date?: string;
    patient_sex?: string;
    accession_number?: string;
    modality?: string;
    requested_procedure_desc?: string;
    referring_physician?: string;
    priority?: string;
    protocol_name?: string;
  };
  findings?: string;
  impression?: string;
  recommendations?: string;
  signedBy?: string;
  signedAt?: string;
  /** Left rail for the masthead (used by staff surfaces); portal omits it. */
  children?: React.ReactNode;
}

/**
 * Branded diagnostic imaging report document — faithful to
 * design-system/quantumpacs/REPORT-TEMPLATE.html: dark masthead band with
 * the Orbit mark + QuantumPACS wordmark, tenant co-brand, kv table, ACR
 * sections, teal impression box, signature block, confidential footer.
 */
export default function ReportDocument({
  tenantName,
  meta = {},
  findings,
  impression,
  recommendations,
  signedBy,
  signedAt,
  children,
}: ReportDocumentProps) {
  const { user } = useAuth();
  const facility = tenantName || user?.tenant_name || "Imaging Services";

  return (
    <div className="rpt">
      <div className="rpt-head">
        <div className="rpt-brand">
          <svg
            className="rpt-logo"
            width="34"
            height="34"
            viewBox="0 0 40 40"
            fill="none"
            aria-label="QuantumPACS Orbit logo"
          >
            <circle cx="20" cy="20" r="18" stroke="#22D3EE" strokeWidth="3" />
            <circle
              cx="20"
              cy="20"
              r="10"
              stroke="#67E8F9"
              strokeWidth="2"
              opacity="0.55"
            />
            <line
              x1="20"
              y1="2"
              x2="20"
              y2="10"
              stroke="#22D3EE"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <line
              x1="20"
              y1="30"
              x2="20"
              y2="38"
              stroke="#22D3EE"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <ellipse
              cx="20"
              cy="20"
              rx="6"
              ry="2.5"
              stroke="#34D399"
              strokeWidth="1.5"
              opacity="0.7"
            />
            <circle cx="20" cy="20" r="2.5" fill="#22D3EE" />
          </svg>
          <div>
            <div className="rpt-wordmark">
              Quantum<span className="rpt-pacs">PACS</span>
            </div>
            <div className="rpt-facility">Diagnostic Imaging Platform</div>
          </div>
        </div>

        <div className="rpt-cobrand">
          <span className="rpt-cobrand-label">Operated by</span>
          <span className="rpt-cobrand-name">{facility}</span>
        </div>

        <div className="rpt-title">
          <div className="rpt-doctype">Diagnostic Imaging Report</div>
          <div className="rpt-status">Final</div>
          <div className="rpt-docid">{meta.accession_number || "—"}</div>
        </div>
      </div>

      <div className="rpt-body">
        {children}

        <table className="rpt-kv" role="presentation">
          <tbody>
            <tr>
              <th scope="row">Patient Name</th>
              <td>{meta.patient_name || "—"}</td>
              <th scope="row">Patient ID / MRN</th>
              <td className="rpt-mono">{meta.patient_id || "—"}</td>
            </tr>
            <tr>
              <th scope="row">Date of Birth</th>
              <td>{meta.patient_birth_date || "—"}</td>
              <th scope="row">Sex</th>
              <td>{meta.patient_sex || "—"}</td>
            </tr>
            <tr>
              <th scope="row">Accession #</th>
              <td className="rpt-mono">{meta.accession_number || "—"}</td>
              <th scope="row">Modality</th>
              <td>{meta.modality || "—"}</td>
            </tr>
            <tr>
              <th scope="row">Study Description</th>
              <td>{meta.requested_procedure_desc || "—"}</td>
              <th scope="row">Priority</th>
              <td>{meta.priority || "—"}</td>
            </tr>
            <tr>
              <th scope="row">Referring Physician</th>
              <td>{meta.referring_physician || "—"}</td>
              <th scope="row">Protocol</th>
              <td>{meta.protocol_name || "—"}</td>
            </tr>
          </tbody>
        </table>

        <section className="rpt-section">
          <h2 className="rpt-label">Findings</h2>
          {findings ? (
            <p className="rpt-text">{findings}</p>
          ) : (
            <p className="rpt-text">
              <span className="rpt-ph">No findings documented.</span>
            </p>
          )}
        </section>

        <div className="rpt-impression">
          <h2 className="rpt-label">Impression</h2>
          {impression ? (
            <p className="rpt-text">{impression}</p>
          ) : (
            <p className="rpt-text">
              <span className="rpt-ph">No impression documented.</span>
            </p>
          )}
        </div>

        {recommendations ? (
          <section className="rpt-section">
            <h2 className="rpt-label">Recommendations</h2>
            <p className="rpt-text">{recommendations}</p>
          </section>
        ) : null}

        <div className="rpt-sign">
          <div>
            <div className="rpt-sig-line">Electronically signed</div>
            <div className="rpt-sig-name">{signedBy || "—"}</div>
            <div className="rpt-sig-creds">Staff Radiologist</div>
          </div>
          <div className="rpt-sig-meta">
            <div className="rpt-mono">
              {signedAt ? new Date(signedAt).toLocaleString() : "—"}
            </div>
            <div>
              Report status: <strong>FINAL</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="rpt-foot">
        <p>
          <span className="rpt-phi">
            CONFIDENTIAL — PROTECTED HEALTH INFORMATION.
          </span>
          This report is intended solely for the use of the patient and their
          healthcare providers. Unauthorized use or disclosure is prohibited by
          law. Generated by QuantumPACS for {facility}.
        </p>
      </div>
    </div>
  );
}