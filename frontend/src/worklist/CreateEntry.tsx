import { Form, Input, Select, DatePicker, TimePicker } from "antd";

const MODALITIES = [
  "CT",
  "MR",
  "XA",
  "US",
  "NM",
  "PET",
  "PT",
  "DX",
  "CR",
  "MG",
  "IO",
  "RF",
  "SC",
  "OT",
  "BI",
  "SR",
  "SEG",
  "REG",
];

interface CreateEntryProps {
  form: any;
  editingEntry?: any | null;
}

export function CreateEntry({ form, editingEntry }: CreateEntryProps) {
  return (
    <Form form={form} layout="vertical">
      <Form.Item
        name="patient_id"
        label="Patient ID"
        rules={[{ required: true }]}
      >
        <Input placeholder="e.g., PAT-00123" />
      </Form.Item>
      <Form.Item name="patient_name" label="Patient Name">
        <Input placeholder="Last^First Middle" />
      </Form.Item>
      <div style={{ display: "flex", gap: 12 }}>
        <Form.Item
          name="patient_birth_date"
          label="Birth Date"
          style={{ flex: 1 }}
        >
          <Input placeholder="YYYY-MM-DD" />
        </Form.Item>
        <Form.Item name="patient_sex" label="Sex" style={{ flex: 1 }}>
          <Select allowClear placeholder="Select">
            <Select.Option value="M">Male</Select.Option>
            <Select.Option value="F">Female</Select.Option>
            <Select.Option value="O">Other</Select.Option>
          </Select>
        </Form.Item>
      </div>
      <Form.Item name="accession_number" label="Accession #">
        <Input placeholder="e.g., ACC-98765" />
      </Form.Item>
      <Form.Item name="requested_procedure_desc" label="Procedure Description">
        <Input placeholder="e.g., CT CHEST W CONTRAST" />
      </Form.Item>
      <div style={{ display: "flex", gap: 12 }}>
        <Form.Item name="modality" label="Modality" style={{ flex: 1 }}>
          <Select allowClear placeholder="Select modality" showSearch>
            {MODALITIES.map((m) => (
              <Select.Option key={m} value={m}>
                {m}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item
          name="requested_procedure_id"
          label="Procedure ID"
          style={{ flex: 1 }}
        >
          <Input placeholder="e.g., RP-001" />
        </Form.Item>
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <Form.Item
          name="scheduled_date"
          label="Scheduled Date"
          style={{ flex: 1 }}
        >
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          name="scheduled_time"
          label="Scheduled Time"
          style={{ flex: 1 }}
        >
          <TimePicker style={{ width: "100%" }} format="HH:mm" />
        </Form.Item>
      </div>
      <Form.Item name="station_ae_title" label="Station AE Title">
        <Select
          allowClear
          placeholder="Select or type AE title"
          mode="tags"
          maxCount={1}
          onChange={() => {}}
        >
          <Select.Option value="OPENPACS_SCANNER_1">
            OPENPACS_SCANNER_1
          </Select.Option>
          <Select.Option value="OPENPACS_SCANNER_2">
            OPENPACS_SCANNER_2
          </Select.Option>
          <Select.Option value="CT_ROOM_1">CT_ROOM_1</Select.Option>
          <Select.Option value="MR_ROOM_1">MR_ROOM_1</Select.Option>
          <Select.Option value="XA_SUITE_1">XA_SUITE_1</Select.Option>
        </Select>
      </Form.Item>
    </Form>
  );
}
