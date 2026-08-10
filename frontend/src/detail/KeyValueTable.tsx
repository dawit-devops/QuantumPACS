import { useMemo, useState } from "react";
import { Input, Table } from "antd";

interface MetaRow {
  key: string;
  value: string;
}

interface KeyValueTableProps {
  file: { id: string | number; meta?: Record<string, unknown> };
  loading?: boolean;
  pagination?: false | { pageSize?: number };
  rowKey?: (record: MetaRow) => string;
  style?: React.CSSProperties;
}

// Read-only key/value metadata table. The inline-edit machinery that used to
// live here was never reachable (editableFields was always empty) and was
// removed in Sprint 3 (Q-C1) — DICOM tags are edited via the tag API, not
// inline cell editing.
const KeyValueTable = ({
  file,
  loading,
  pagination,
  rowKey,
  style,
}: KeyValueTableProps) => {
  const [search, setSearch] = useState("");

  // (R1-05) Rows are derived in render instead of two useEffects that
  // setDataSource — the old effect reset the search on every new file, and
  // the two effects could transiently disagree (stale datasource for the new
  // file while the search effect re-ran). Deriving keeps the datasource
  // consistent with the current file + search on every render.
  const rows = useMemo(() => {
    const all = Object.entries(file.meta || {})
      .map(([key, value]) => ({ key, value: String(value) }))
      .sort((a, b) => a.key.localeCompare(b.key));
    const q = search.toLowerCase();
    return all.filter((d) => d.key.toLowerCase().startsWith(q));
  }, [file, search]);

  return (
    <div style={style}>
      <Input
        placeholder="Search..."
        onChange={(e) => setSearch(e.target.value)}
        value={search}
      />
      <Table
        scroll={{ x: 500 }}
        bordered
        dataSource={rows}
        columns={[
          { title: "key", dataIndex: "key", width: "20%" },
          { title: "value", dataIndex: "value", width: "70%" },
        ]}
        loading={loading}
        pagination={pagination}
        rowKey={rowKey}
      />
    </div>
  );
};

export default KeyValueTable;
