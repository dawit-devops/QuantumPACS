import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import Highlighter from "react-highlight-words";
import {
  App,
  Layout,
  Table,
  Input,
  Button,
  Row,
  Col,
  Grid,
  Card,
  Tag,
  Alert,
} from "antd";
import type { InputRef } from "antd";
import type { ColumnType } from "antd/es/table";
import { SearchOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { open } from "../helpers";
import { qidoSearch, searchFiles, DicomJsonObject } from "../api/files";
import { useAuth } from "../auth/AuthContext";
import { isAdminScopedRole } from "../navigator";
import { PageState } from "../common/PageState";
import PageHeader from "../common/PageHeader";
import { AdminFiles } from "./AdminFiles";
import AdvancedSearch from "./AdvancedSearch";
import { PAGINATION } from "../config";
import { useTenantRefetch } from "../hooks";
import "./Files.css";

const Content = Layout.Content;
// Flat row shape both the QIDO path and the ES fallback produce — the
// columns render from string keys, so the row type is a string map.
export type FileRow = Record<string, string>;

// (P-M4) Hard ceiling on QIDO results rendered in the table; prevents an
// unbounded study list from ballooning the DOM.
const QIDO_RESULT_CAP = 100;

const Search = Input.Search;

function encodeUrl(obj: Record<string, unknown>) {
  return "?" + encodeURIComponent(JSON.stringify(obj));
}

function decodeUrl(url: string): Record<string, unknown> {
  if (!url.length) return {};
  try {
    return JSON.parse(decodeURIComponent(url.slice(1)));
  } catch {
    // A truncated or hand-edited search string must not crash the browser
    // (M2) — fall back to an empty search instead.
    return {};
  }
}

const initialAdvancedFields = [
  ["Patient ID", ""],
  ["Patient's Name", ""],
  ["Patient's Age", ""],
  ["Patient's Gender", ""],
  ["Study ID", ""],
  ["Study Description", ""],
  ["Series Number", ""],
  ["Series Modality", ""],
  ["Series Description", ""],
  ["Referring Physician's Name", ""],
  ["Performing Physician's Name", ""],
  ["SOP Class UID", ""],
];

function extractDicomValue(tag: DicomJsonObject | undefined): string {
  if (!tag || !tag.Value) return "";
  const values = tag.Value as unknown[];
  if (typeof values[0] === "object" && values[0] !== null) {
    return (values as Record<string, unknown>[])
      .map((v) => v.Alphabetic || v.Value || "")
      .join(" ");
  }
  return values.join(" ");
}

function dicomJsonToFlat(studies: DicomJsonObject[]): FileRow[] {
  return studies.map((s) => ({
    id: extractDicomValue(s["0020000D"] as DicomJsonObject),
    "Patient ID": extractDicomValue(s["00100020"] as DicomJsonObject),
    "Patient's Name": extractDicomValue(s["00100010"] as DicomJsonObject),
    "Study ID": extractDicomValue(s["0020000D"] as DicomJsonObject),
    "Study Description": extractDicomValue(s["00081030"] as DicomJsonObject),
    Modality: extractDicomValue(s["00080060"] as DicomJsonObject),
    "Accession Number": extractDicomValue(s["00080050"] as DicomJsonObject),
    "Study Date": extractDicomValue(s["00080020"] as DicomJsonObject),
    "Series Number": extractDicomValue(s["00200011"] as DicomJsonObject),
    "Series Description": extractDicomValue(s["0008103E"] as DicomJsonObject),
  }));
}

function searchToQidoParams(
  searchObj: Record<string, unknown>,
): Record<string, string> {
  const params: Record<string, string> = {};
  const fieldMap: Record<string, string> = {
    "Patient ID": "PatientID",
    "Study ID": "StudyInstanceUID",
    "Accession Number": "AccessionNumber",
    Modality: "Modality",
    query: "PatientID",
  };
  for (const [field, value] of Object.entries(searchObj)) {
    if (field in fieldMap && value && String(value).trim()) {
      params[fieldMap[field]] = String(value).trim();
    }
  }
  return params;
}

function Files() {
  const { message } = App.useApp();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const navigate = useNavigate();
  const location = useLocation();
  // Admin-scoped roles manage files but not patients; the patient column
  // stays readable as plain text so no dead link into the gated /patients.
  const { user, hasPermission } = useAuth();
  const isAdminScoped = isAdminScopedRole(user?.role);
  // The backend re-checks FILE_WRITE on POST /files/upload, so the button is
  // hidden client-side for roles without the grant (mirrors nav gating).
  const canUpload = hasPermission("FILE_WRITE");

  const [data, setData] = useState<FileRow[]>([]);
  // (R1-05) The mobile card list paginates instead of animating up to 100
  // cards with per-row stagger delays (each card paid a 0–3s animation-delay
  // on scroll-in); 20-card chunks keep the initial paint cheap.
  const MOBILE_PAGE_SIZE = 20;
  const [mobilePage, setMobilePage] = useState(1);
  const [pagination, setPagination] = useState<{
    pageSize: number;
    current?: number;
    total?: number;
  }>({ pageSize: PAGINATION.limit });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const searchInput = useRef<InputRef>(null);
  const [globSearchCurrent, setGlobSearchCurrent] = useState("");
  const [globSearch, setGlobSearch] = useState("");
  const [searchText, setSearchText] = useState("");
  const [advancedFields, setAdvancedFields] = useState(
    initialAdvancedFields.map((e) => [...e]),
  );
  const [selected, setSelected] = useState<FileRow[]>([]);
  // P2-5 (tenant_admin review): when the search backend is down the empty
  // table is a degradation, not an empty archive — the response carries
  // search_available:false and the page shows a notice instead of the bare
  // "No files uploaded" copy.
  const [searchAvailable, setSearchAvailable] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    const pager = { ...pagination };
    pager.current = pagination.current;
    setPagination(
      Object.assign({}, pagination, { current: pagination.current }),
    );
    let s: any = {
      results: pagination.pageSize,
      page: pagination.current,
      sortField: sorter.field,
      sortOrder: sorter.order,
      ...filters,
    };
    if (globSearch) {
      s.query = globSearch;
    }
    if (advancedFields) {
      const so: any = {};
      for (const f of advancedFields) {
        if (!f[0].length || !f[1].length) continue;
        so[f[0]] = [f[1]];
      }
      s = Object.assign(s, so);
    }
    navigate(encodeUrl(s));
  };

  const fetchQidoResults = (
    qidoParams: Record<string, string>,
  ): Promise<FileRow[]> => {
    // (P-M4) Explicit limit: the backend caps at 100 by default, but passing
    // it keeps the frontend contract stable if that default ever changes.
    const capped = { ...qidoParams, limit: String(QIDO_RESULT_CAP) };
    return qidoSearch(capped).then((results) =>
      dicomJsonToFlat(results).slice(0, QIDO_RESULT_CAP),
    );
  };

  const fetch = () => {
    setLoading(true);
    setError(null);
    const searchObj = decodeUrl(window.location.search);
    if (searchObj.query) {
      setGlobSearch(String(searchObj.query));
      setSearchText("");
    } else {
      let set = false;
      for (const k in searchObj) {
        if (Array.isArray(searchObj[k])) {
          setSearchText(searchObj[k][0]);
          setGlobSearch("");
          set = true;
        }
      }
      if (!set) {
        setGlobSearch("");
        setSearchText("");
      }
    }
    const qidoParams = searchToQidoParams(searchObj);
    const hasQidoParams = Object.keys(qidoParams).length > 0;
    if (hasQidoParams) {
      fetchQidoResults(qidoParams)
        .then((results: FileRow[]) => {
          setLoading(false);
          if (results.length > 0) {
            setData(results);
            // Functional update: `pagination` in this closure may be stale
            // (P-M3) — merging total into the latest state avoids resurrecting
            // an old page after a race between search and page change.
            setPagination((prev) =>
              Object.assign({}, prev, { total: results.length }),
            );
            return;
          }
          fallbackToV2(searchObj);
        })
        .catch(() => {
          fallbackToV2(searchObj);
        });
    } else {
      fallbackToV2(searchObj);
    }
  };

  useEffect(() => {
    // fetch is intentionally omitted: it is recreated every render, and the
    // URL search (via useLocation) is the only thing that must trigger a
    // reload here.
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  // Tenant switch → refetch: the QIDO search is scoped server-side via the
  // X-Tenant-ID header, so results must not linger from the old tenant.
  useTenantRefetch(fetch);

  // No second mount effect for PAGINATION.limit — it is a module constant,
  // so a separate effect would fire once on mount and duplicate the first
  // search request (P-M3).

  const fallbackToV2 = (searchObj: Record<string, unknown>) => {
    searchFiles(searchObj)
      .then((data) => {
        setLoading(false);
        // ES fallback rows are loosely-typed docs; the table only reads the
        // flat string keys shared with the QIDO path.
        setData(data.data as FileRow[]);
        setPagination((prev) => Object.assign({}, prev, { total: data.total }));
        // P2-5: the backend marks the response when search was unavailable;
        // absent flag (truthy) keeps the normal path untouched.
        setSearchAvailable(data.search_available !== false);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  };

  const downloadFiles = () => {
    if (!selected || !selected.length) return;

    open("files/download.zip?ids=" + selected.join(",")).catch(() => {
      message.error("Fail to download");
    });
  };

  const downloadData = () => {
    if (!selected || !selected.length) return;

    open("files/download.csv?ids=" + selected.join(",")).catch(() => {
      message.error("Fail to download");
    });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPagination(Object.assign({}, pagination, { current: 1 }));
    setGlobSearchCurrent(e.target.value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      handleSearch(e.target.value);
    }, 300);
  };

  const handleSearch = (value: string) => {
    setAdvancedFields(initialAdvancedFields.map((e) => [...e]));
    setSearchText("");
    setGlobSearch(value);
    if (value) {
      navigate(encodeUrl({ query: value }));
    } else {
      navigate("");
    }
  };

  const getColumnSearchProps = <T extends object>(
    dataIndex: string,
    options: { render?: (text: string, record: T) => React.ReactNode } = {},
  ): ColumnType<T> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }: any) => (
      <div style={{ padding: 8 }}>
        <Input
          ref={(node) => {
            (searchInput as any).current = node;
          }}
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e: any) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => handleColumnSearch(selectedKeys, confirm)}
          style={{ width: 188, marginBottom: 8, display: "block" }}
        />
        <Button
          type="primary"
          onClick={() => handleColumnSearch(selectedKeys, confirm)}
          icon={<SearchOutlined />}
          size="small"
          style={{ width: 90, marginRight: 8 }}
        >
          Search
        </Button>
        <Button
          onClick={() => handleReset(clearFilters)}
          size="small"
          style={{ width: 90 }}
        >
          Reset
        </Button>
      </div>
    ),
    filterIcon: (filtered: any) => (
      <SearchOutlined
        style={{ color: filtered ? "var(--color-blue-500)" : undefined }}
      />
    ),
    filterDropdownProps: {
      onOpenChange: (visible: any) => {
        if (visible) {
          setTimeout(() => (searchInput.current as any)?.select());
        }
      },
    },
    render: (text: any, record: T) => {
      if (options.render) {
        return options.render(text, record);
      }
      const searchWords = [searchText];
      if (globSearch) {
        searchWords.push(globSearch);
      }
      return (
        <Highlighter
          highlightStyle={{
            backgroundColor: "var(--table-highlight-bg)",
            padding: 0,
          }}
          searchWords={searchWords}
          autoEscape
          textToHighlight={text ? text.toString() : ""}
        />
      );
    },
  });

  const handleColumnSearch = (
    selectedKeys: readonly React.Key[],
    confirm: () => void,
  ) => {
    confirm();
    setPagination(Object.assign({}, pagination, { current: 1 }));
    setGlobSearchCurrent("");
    setGlobSearch("");
    setSearchText(selectedKeys[0] !== undefined ? String(selectedKeys[0]) : "");
  };

  const handleReset = (clearFilters?: () => void) => {
    clearFilters?.();
    setSearchText("");
  };

  const onAdvancedSearchChangeLabel = (
    i: number,
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    // Functional update: mutating advancedFields[i] in place before setState
    // (R1-05) could hand React an already-mutated array — the new array
    // spread then aliased the mutated rows and the label edit leaked into
    // onAdvancedSearch's snapshot even before commit.
    setAdvancedFields((prev) =>
      prev.map((f, j) => (j === i ? [e.target.value, f[1]] : f)),
    );
  };

  const onAdvancedSearchChange = (
    i: number,
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setAdvancedFields((prev) =>
      prev.map((f, j) => (j === i ? [f[0], e.target.value] : f)),
    );
  };

  const onAdvancedSearchAdd = () => {
    setAdvancedFields((prev) => [...prev, ["", ""]]);
  };

  const onAdvancedSearchRemove = (i: number) => {
    setAdvancedFields((prev) => prev.filter((_, j) => j !== i));
  };

  const onAdvancedSearch = () => {
    setSearchText("");
    setGlobSearchCurrent("");
    setGlobSearch("");
    setShowAdvanced(false);
    const so: Record<string, string[]> = {};
    for (const f of advancedFields) {
      if (!f[0].length || !f[1].length) continue;
      so[f[0]] = [f[1]];
    }
    navigate(encodeUrl(so));
  };

  const columns: ColumnType<FileRow>[] = [
    {
      title: "ID",
      dataIndex: "id",
      render: (text: string, record: FileRow) => (
        <Link to={"/files/" + record.id}>{text}</Link>
      ),
    },
    {
      title: "Patient ID",
      dataIndex: "Patient ID",
      ...getColumnSearchProps<FileRow>("Patient ID", {
        render: (text: string, record: FileRow) =>
          isAdminScoped ? (
            <span>{text}</span>
          ) : (
            <Link to={"/patients/" + record.patient_db_id}>{text}</Link>
          ),
      }),
    },
    {
      title: "Patient Name",
      dataIndex: "Patient's Name",
      ...getColumnSearchProps<FileRow>("Patient's Name"),
    },
    {
      title: "Study ID",
      dataIndex: "Study ID",
      ...getColumnSearchProps<FileRow>("Study ID"),
    },
    {
      title: "Study Description",
      dataIndex: "Study Description",
      ...getColumnSearchProps<FileRow>("Study Description"),
    },
    {
      title: "Series Number",
      dataIndex: "Series Number",
      ...getColumnSearchProps<FileRow>("Series Number"),
    },
    {
      title: "Series Description",
      dataIndex: "Series Description",
      ...getColumnSearchProps<FileRow>("Series Description"),
    },
    {
      title: "Modality",
      dataIndex: "Modality",
      render: (text: string) => (text ? <Tag>{text}</Tag> : "-"),
    },
    {
      title: "Accession",
      dataIndex: "Accession Number",
      width: "12%",
    },
    {
      title: "Date",
      dataIndex: "Study Date",
      width: "12%",
      render: (text: string) => text || "-",
      sorter: true,
    },
  ];

  const rowSelection = {
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelected(
        selectedRowKeys
          .map((k) => data.find((r) => r.id === String(k)))
          .filter(Boolean) as FileRow[],
      );
    },
    getCheckboxProps: (record: FileRow) => ({
      disabled: false,
      name: record.name,
    }),
  };

  return (
    <Content className="files">
      <PageHeader
        title="Files"
        description="Search uploaded studies and images"
      />
      <Row>
        <Col span={16}>
          <Search
            data-testid="files-search-input"
            placeholder="input search text"
            enterButton="Search"
            size="large"
            onSearch={handleSearch}
            style={{
              marginBottom: 10,
            }}
            value={globSearchCurrent}
            onChange={handleSearchChange}
          />
        </Col>
        <Col span={8}>
          <Button
            size="large"
            type="primary"
            onClick={() => setShowAdvanced(true)}
          >
            Advanced
          </Button>
        </Col>
      </Row>
      {canUpload && (
        <Button
          style={{ marginBottom: "10px" }}
          type="primary"
          onClick={() => setShowUpload(true)}
        >
          Upload
        </Button>
      )}
      <Button
        style={{ marginBottom: "10px", marginLeft: "5px" }}
        type="primary"
        onClick={() => downloadFiles()}
      >
        Download files
      </Button>
      <Button
        style={{ marginBottom: "10px", marginLeft: "5px" }}
        type="primary"
        onClick={() => downloadData()}
      >
        Download data
      </Button>
      <AdvancedSearch
        visible={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        onSearch={onAdvancedSearch}
        fields={advancedFields}
        onChangeLabel={onAdvancedSearchChangeLabel as any}
        onChange={onAdvancedSearchChange as any}
        onAdd={onAdvancedSearchAdd}
        onRemove={onAdvancedSearchRemove}
        fixed={initialAdvancedFields.length}
      />
      <AdminFiles
        visible={showUpload}
        reload={fetch}
        onClose={() => setShowUpload(false)}
      />
      {!searchAvailable && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Search is unavailable"
          description="The search service is down — archived files are not listed right now. Uploads still work."
        />
      )}
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage={
          !searchAvailable
            ? "Search is unavailable — no archive results can be shown."
            : globSearch || searchText
              ? "No files match your search"
              : "No files uploaded"
        }
      >
        {isMobile ? (
          <div
            className="stagger-enter"
            style={{ display: "flex", flexDirection: "column", gap: 8 }}
          >
            {data
              .slice(0, mobilePage * MOBILE_PAGE_SIZE)
              .map((item: FileRow) => (
                <Card key={item.id} size="small" hoverable>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                    }}
                  >
                    <div>
                      {/* (R1-05) Real link (was a div onClick) so the whole
                        title is keyboard-activatable and mid-link
                        open-in-new-tab works. */}
                      <Link
                        to={`/files/${item.id}`}
                        style={{ fontWeight: 600, fontSize: 14 }}
                      >
                        {item["Patient ID"] || item.id}
                      </Link>
                      <div
                        style={{
                          fontSize: 13,
                          color: "var(--text-secondary)",
                          marginTop: 2,
                        }}
                      >
                        {item["Patient's Name"] || item.patient_name || "-"}
                      </div>
                    </div>
                    {item.Modality && <Tag>{item.Modality}</Tag>}
                  </div>
                  {(item["Study Description"] || item.study_description) && (
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--text-secondary)",
                        marginTop: 4,
                      }}
                    >
                      {item["Study Description"] || item.study_description}
                    </div>
                  )}
                </Card>
              ))}
            {data.length > mobilePage * MOBILE_PAGE_SIZE && (
              <Button
                type="default"
                block
                onClick={() => setMobilePage((p) => p + 1)}
                style={{ marginTop: 4 }}
              >
                Load more ({data.length - mobilePage * MOBILE_PAGE_SIZE}{" "}
                remaining)
              </Button>
            )}
          </div>
        ) : (
          <Table
            className="filesTable"
            scroll={{ x: 500 }}
            columns={columns}
            rowKey={(record: FileRow) => record.id}
            dataSource={data}
            rowSelection={rowSelection}
            pagination={pagination}
            loading={loading}
            onChange={handleTableChange}
            rowClassName={() => "stagger-enter"}
            onRow={(_: FileRow, index?: number) => ({
              style: { "--stagger-index": index ?? 0 } as React.CSSProperties,
            })}
          />
        )}
      </PageState>
    </Content>
  );
}

export default withSidebar(Files);
