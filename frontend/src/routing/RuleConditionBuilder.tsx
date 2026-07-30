import { useState, useEffect } from 'react';
import { Button, Select, Input, InputNumber, Tag, Space } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';

const CONDITION_FIELDS = [
  'modality', 'study_description', 'patient_id',
  'accession_number', 'station_ae_title', 'priority',
];

const CONDITION_OPS = [
  'equals', 'not_equals', 'contains', 'not_contains',
  'greater_than', 'less_than', 'exists',
];

const OP_LABELS: Record<string, string> = {
  equals: '=',
  not_equals: '≠',
  contains: 'contains',
  not_contains: 'not contains',
  greater_than: '>',
  less_than: '<',
  exists: 'exists',
};

function valueInput(field: string, op: string, value: string, onChange: (v: string) => void) {
  if (field === 'modality') {
    return (
      <Select value={value || undefined} onChange={onChange} placeholder="Value" allowClear style={{ minWidth: 120 }} showSearch>
        {['CT', 'MR', 'XA', 'US', 'NM', 'PET', 'PT', 'DX', 'CR', 'MG', 'IO', 'RF', 'SC', 'OT'].map((m) => (
          <Select.Option key={m} value={m}>{m}</Select.Option>
        ))}
      </Select>
    );
  }
  if (field === 'priority') {
    return (
      <InputNumber value={value ? Number(value) : undefined} onChange={(v) => onChange(String(v ?? ''))} placeholder="Value" min={0} style={{ width: 100 }} />
    );
  }
  return <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Value" style={{ width: 180 }} />;
}

interface ConditionRow {
  field: string;
  op: string;
  value: string;
}

interface RuleConditionBuilderProps {
  value?: Record<string, any>;
  onChange?: (conditions: Record<string, any>) => void;
}

export function RuleConditionBuilder({ value, onChange }: RuleConditionBuilderProps) {
  const [rows, setRows] = useState<ConditionRow[]>([]);

  useEffect(() => {
    if (value && Object.keys(value).length > 0) {
      const parsed: ConditionRow[] = [];
      for (const [field, raw] of Object.entries(value)) {
        if (typeof raw === 'object' && raw !== null) {
          const entries = Object.entries(raw as Record<string, any>);
          if (entries.length === 1) {
            const [op, val] = entries[0];
            parsed.push({ field, op: op === '$eq' ? 'equals' : op === '$ne' ? 'not_equals' : op === '$gt' ? 'greater_than' : op === '$lt' ? 'less_than' : op === '$exists' ? 'exists' : op === '$contains' ? 'contains' : op, value: String(val ?? '') });
          } else {
            parsed.push({ field, op: 'equals', value: JSON.stringify(raw) });
          }
        } else {
          parsed.push({ field, op: 'equals', value: String(raw ?? '') });
        }
      }
      setRows(parsed.length > 0 ? parsed : [{ field: 'modality', op: 'equals', value: '' }]);
    } else {
      setRows([{ field: 'modality', op: 'equals', value: '' }]);
    }
  }, [value]);

  const emit = (newRows: ConditionRow[]) => {
    const conditions: Record<string, any> = {};
    for (const row of newRows) {
      if (!row.field) continue;
      if (row.op === 'equals') {
        conditions[row.field] = row.value;
      } else if (row.op === 'contains') {
        conditions[row.field] = { $contains: row.value };
      } else if (row.op === 'not_contains') {
        conditions[row.field] = { $notContains: row.value };
      } else if (row.op === 'greater_than') {
        conditions[row.field] = { $gt: Number(row.value) };
      } else if (row.op === 'less_than') {
        conditions[row.field] = { $lt: Number(row.value) };
      } else if (row.op === 'exists') {
        conditions[row.field] = { $exists: true };
      } else if (row.op === 'not_equals') {
        conditions[row.field] = { $ne: row.value };
      }
    }
    onChange?.(conditions);
  };

  const updateRow = (index: number, patch: Partial<ConditionRow>) => {
    const next = rows.map((r, i) => (i === index ? { ...r, ...patch } : r));
    setRows(next);
    emit(next);
  };

  const addRow = () => {
    const next = [...rows, { field: 'modality', op: 'equals', value: '' }];
    setRows(next);
  };

  const removeRow = (index: number) => {
    const next = rows.filter((_, i) => i !== index);
    setRows(next.length > 0 ? next : [{ field: 'modality', op: 'equals', value: '' }]);
    emit(next.length > 0 ? next : [{ field: 'modality', op: 'equals', value: '' }]);
  };

  return (
    <div>
      {rows.map((row, i) => (
        <Space key={i} style={{ display: 'flex', marginBottom: 8 }} align="start">
          <Select
            value={row.field}
            onChange={(v) => updateRow(i, { field: v, op: 'equals', value: '' })}
            style={{ minWidth: 160 }}
            options={CONDITION_FIELDS.map((f) => ({ value: f, label: f.replace(/_/g, ' ') }))}
          />
          <Select
            value={row.op}
            onChange={(v) => updateRow(i, { op: v, value: '' })}
            style={{ minWidth: 110 }}
            options={CONDITION_OPS.map((o) => ({ value: o, label: OP_LABELS[o] }))}
          />
          {row.op !== 'exists' && valueInput(row.field, row.op, row.value, (v) => updateRow(i, { value: v }))}
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeRow(i)} aria-label="Remove condition" />
        </Space>
      ))}
      <Button type="dashed" onClick={addRow} icon={<PlusOutlined />} size="small">
        Add condition
      </Button>
      {rows.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Tag color="blue">AND</Tag>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>All conditions must match</span>
        </div>
      )}
    </div>
  );
}
