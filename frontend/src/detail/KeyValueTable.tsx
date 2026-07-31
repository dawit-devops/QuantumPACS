import { useEffect, useState } from "react";
import { Input, Table } from "antd";

interface MetaRow {
  key: string;
  value: string;
}

interface KeyValueTableProps {
  file: { id: string; meta?: Record<string, string> };
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
  const [dataSource, setDataSource] = useState<MetaRow[]>([]);
  const [search, setSearch] = useState("");

  const metaToDatasource = (): MetaRow[] =>
    Object.entries(file.meta || {})
      .map(([key, value]) => ({ key, value }))
      .sort((a, b) => a.key.localeCompare(b.key));

  useEffect(() => {
    setDataSource(metaToDatasource());
    setSearch("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file]);

  useEffect(() => {
    setDataSource(
      metaToDatasource().filter((d) =>
        d.key.toLowerCase().startsWith(search.toLowerCase()),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

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
        dataSource={dataSource}
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
