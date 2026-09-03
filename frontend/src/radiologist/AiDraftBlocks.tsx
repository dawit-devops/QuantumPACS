import React, { useState } from "react";
import { Button, Checkbox, Modal, Tag, Tooltip } from "antd";
import {
  CheckOutlined,
  CloseOutlined,
  RedoOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  CheckSquareOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import type { AiDraftBlock, AiDraftSection } from "./aiDraftTypes";
import { AI_DRAFT_SECTION_LABELS } from "./aiDraftTypes";
import type { AiReportDraftApi } from "./useAiReportDraft";
import "./AiDraftBlocks.css";

interface AiDraftBlocksProps {
  draft: AiReportDraftApi;
  section: AiDraftSection;
}

/**
 * Per-section AI-drafted report block list (Part A).
 *
 * A.3 states are always visible: unreviewed blocks keep a violet left-rule +
 * faint wash + `✨ AI-drafted` mono tag; the moment the radiologist accepts
 * (or edits in place) the violet styling is dropped and the text is theirs.
 *
 * A.4: per-block Accept (✓) / Reject (✕) in the left gutter, plus a
 * per-block regenerate (↻) that cycles the "v2 of N" version stepper.
 */
export default function AiDraftBlocks({ draft, section }: AiDraftBlocksProps) {
  const blocks = draft.blocksForSection(section);
  const [showLog, setShowLog] = useState(false);

  // The changelog toggle stays reachable from the Findings section even when
  // every draft is resolved — A.7 requires the audit trail to remain
  // accessible independent of the working document.
  const logToggle =
    section === "findings" ? (
      <Button
        size="small"
        type="text"
        className="ai-draft-log-toggle"
        icon={<HistoryOutlined />}
        onClick={() => setShowLog(true)}
      >
        AI draft log
      </Button>
    ) : null;

  if (blocks.length === 0) {
    return (
      <>
        {logToggle}
        <AiDraftLog open={showLog} onClose={() => setShowLog(false)} draft={draft} />
      </>
    );
  }

  return (
    <div className="ai-draft-rows" data-testid={`ai-draft-${section}`}>
      {blocks.map((block) => (
        <AiDraftRow key={block.id} draft={draft} block={block} />
      ))}
      {logToggle}
      <AiDraftLog open={showLog} onClose={() => setShowLog(false)} draft={draft} />
    </div>
  );
}

function AiDraftLog({
  open,
  onClose,
  draft,
}: {
  open: boolean;
  onClose: () => void;
  draft: AiReportDraftApi;
}) {
  return (
    <Modal
      title="AI draft changelog (this session)"
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
    >
      {draft.changelog.length === 0 ? (
        <p className="ai-draft-log-empty">No AI draft actions recorded yet.</p>
      ) : (
        <ul className="ai-draft-log">
          {draft.changelog.map((e) => (
            <li key={e.id}>
              <Tag className="ai-draft-log-action">{e.action}</Tag>
              <strong>{AI_DRAFT_SECTION_LABELS[e.section]}</strong>
              <span className="ai-draft-log-time">
                {new Date(e.timestamp).toLocaleTimeString()}
              </span>
              {e.detail && <div className="ai-draft-log-detail">{e.detail}</div>}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

function AiDraftRow({ draft, block }: { draft: AiReportDraftApi; block: AiDraftBlock }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(block.text);
  const [confirmLog, setConfirmLog] = useState(false);

  const beginEdit = () => {
    setText(block.text);
    setEditing(true);
  };

  // A.3.4: editing the draft in place IS the acceptance gesture — the block
  // converts on blur (Save), never through a separate confirmation dialog.
  const saveEdit = () => {
    setEditing(false);
    draft.editInPlace(block.id, text.trim());
  };

  const confirmAccept = () => {
    draft.acceptBlock(block.id);
    setConfirmLog(false);
  };

  return (
    <div className="ai-draft-row" data-testid={`ai-draft-block-${block.id}`}>
      <div className="ai-draft-gutter">
        <Tooltip title="Accept into report">
          <Button
            size="small"
            type="text"
            className="ai-draft-accept"
            aria-label="Accept AI draft"
            icon={<CheckOutlined />}
            onClick={() => setConfirmLog(true)}
          />
        </Tooltip>
        <Tooltip title="Reject draft">
          <Button
            size="small"
            type="text"
            className="ai-draft-reject"
            aria-label="Reject AI draft"
            icon={<CloseOutlined />}
            onClick={() => draft.rejectBlock(block.id)}
          />
        </Tooltip>
      </div>
      <div className="ai-draft-body">
        <div className="ai-draft-tagrow">
          <span className="ai-draft-tag">
            <ThunderboltOutlined /> AI-drafted
          </span>
          {block.quality === "uncertain" && (
            <Tag className="ai-draft-quality">image quality — verify</Tag>
          )}
          <Tooltip title="Regenerate draft">
            <Button
              size="small"
              type="text"
              className="ai-draft-regenerate"
              aria-label="Regenerate AI draft"
              icon={<RedoOutlined />}
              onClick={() => draft.regenerateBlock(block.id)}
            >
              v{block.version} of {block.totalVersions}
            </Button>
          </Tooltip>
        </div>
        {editing ? (
          <div className="ai-draft-edit">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              aria-label="Edit AI draft text"
            />
            <div className="ai-draft-edit-actions">
              <Button size="small" type="primary" onClick={saveEdit}>
                Save & accept
              </Button>
              <Button size="small" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <button type="button" className="ai-draft-text" onClick={beginEdit} title="Click to edit">
            {block.text}
          </button>
        )}
        {block.priorNote && (
          <div className="ai-draft-prior-note" data-testid="ai-draft-prior-note">
            {block.priorNote}
          </div>
        )}
      </div>
      {/* A.5 confirm modal — acceptance is destructive to the AI styling, not
          the content, so it stays a deliberate recorded action. */}
      <Modal
        title="Accept AI-drafted content?"
        open={confirmLog}
        onCancel={() => setConfirmLog(false)}
        onOk={confirmAccept}
        okText="Accept"
        cancelText="Cancel"
        width={480}
      >
        <p className="ai-draft-confirm-text">{block.text}</p>
        <p className="ai-draft-confirm-hint">
          Accepting makes this your own report text — the AI-drafted styling is
          removed and the action is recorded in the draft log.
        </p>
      </Modal>
    </div>
  );
}

/** Banner shown in the editor header while any unreviewed block exists (A.4). */
export function AiDraftBanner({
  draft,
  onAcceptAll,
  onRejectAll,
}: {
  draft: AiReportDraftApi;
  onAcceptAll: () => void;
  onRejectAll: () => void;
}) {
  if (!draft.hasUnreviewed) return null;
  return (
    <div className="ai-draft-banner" data-testid="ai-draft-banner">
      <span className="ai-draft-banner-title">
        <ThunderboltOutlined /> AI draft — review before signing
      </span>
      <span className="ai-draft-banner-count">
        {draft.unreviewedCount} block{draft.unreviewedCount === 1 ? "" : "s"} need{draft.unreviewedCount === 1 ? "s" : ""} review
      </span>
      <Button size="small" type="primary" icon={<CheckSquareOutlined />} onClick={onAcceptAll}>
        Accept all
      </Button>
      <Button size="small" danger icon={<DeleteOutlined />} onClick={onRejectAll}>
        Discard all
      </Button>
    </div>
  );
}