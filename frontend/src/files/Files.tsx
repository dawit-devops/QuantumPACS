import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router";
import Highlighter from "react-highlight-words";
import { App,
  Layout,
  Table,
  Input,
  Button,
  Row,
  Col,
  Grid,
  Card,
  Tag,
} from "antd";
import type { InputRef } from "antd";
import type { ColumnType } from "antd/es/table";
import { SearchOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { open } from "../helpers";
import { qidoSearch, searchFiles } from "../api/files";
import { PageState } from "../common/PageState";
import { AdminFiles } from "./AdminFiles";
import AdvancedSearch from "./AdvancedSearch";
import { PAGINATION } from "../config";
import "./Files.css";

const Content = Layout.Content;
const Search = Input.Search;

function encodeUrl(obj: any) {
  return "?" + encodeURIComponent(JSON.stringify(obj));
}

function decodeUrl(url: string) {
  if (!url.length) return {};
  return JSON.parse(decodeURIComponent(url.slice(1)));
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

function extractDicomValue(tag: any): string {
  if (!tag || !tag.Value) return "";
  if (typeof tag.Value[0] === "object") {
    return tag.Value.map((v: any) => v.Alphabetic || v.Value || "").join(" ");
  }
  return tag.Value.join(" ");
}

function dicomJsonToFlat(studies: any[]): any[] {
  return studies.map((s: any) => ({
    id: extractDicomValue(s["0020000D"]),
    "Patient ID": extractDicomValue(s["00100020"]),
    "Patient's Name": extractDicomValue(s["00100010"]),
    "Study ID": extractDicomValue(s["0020000D"]),
    "Study Description": extractDicomValue(s["00081030"]),
    Modality: extractDicomValue(s["00080060"]),
    "Accession Number": extractDicomValue(s["00080050"]),
    "Study Date": extractDicomValue(s["00080020"]),
    "Series Number": extractDicomValue(s["00200011"]),
    "Series Description": extractDicomValue(s["0008103E"]),
  }));
}

function searchToQidoParams(searchObj: any): Record<string, string> {
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

function Files(props: any) {
  const { message } = App.useApp();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const navigate = useNavigate();

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({
    pageSize: PAGINATION.limit,
  });
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [showUpload, setShowUpload] = useState(false);
  let [showAdvanced, setShowAdvanced] = useState(false);
  let searchInput = useRef<InputRef>(null);
  let [globSearchCurrent, setGlobSearchCurrent] = useState("");
  let [globSearch, setGlobSearch] = useState("");
  let [searchText, setSearchText] = useState("");
  let [advancedFields, setAdvancedFields] = useState(
    initialAdvancedFields.map((e) => [...e]),
  );
  let [selected, setSelected] = useState<any[]>([]);
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
      let so: any = {};
      for (let f of advancedFields) {
        if (!f[0].length || !f[1].length) continue;
        so[f[0]] = [f[1]];
      }
      s = Object.assign(s, so);
    }
    navigate(encodeUrl(s));
  };

  useEffect(() => {
    fetch();
    // eslint-disable-next-line
  }, [window.location.search]);

  useEffect(() => {
    setPagination(
      Object.assign({}, pagination, { pageSize: PAGINATION.limit }),
    );
    fetch();
    // eslint-disable-next-line
  }, [PAGINATION.limit]);

  const fetchQidoResults = (
    qidoParams: Record<string, string>,
  ): Promise<any[]> => {
    return qidoSearch(qidoParams).then((results) =>
      dicomJsonToFlat(results),
    );
  };

  const fetch = () => {
    setLoading(true);
    setError(null);
    const searchObj = decodeUrl(window.location.search);
    if (searchObj.query) {
      setGlobSearch(searchObj.query);
      setSearchText("");
    } else {
      let set = false;
      for (let k in searchObj) {
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
        .then((results: any[]) => {
          setLoading(false);
          if (results.length > 0) {
            setData(results);
            setPagination(
              Object.assign({}, pagination, { total: results.length }),
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

  const fallbackToV2 = (searchObj: any) => {
    searchFiles(searchObj)
      .then((data) => {
        setLoading(false);
        setData(data.data);
        setPagination(Object.assign({}, pagination, { total: data.total }));
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

  const getColumnSearchProps = (
    dataIndex: string,
    options: any = {},
  ): ColumnType<any> => ({
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
    onFilterDropdownOpenChange: (visible: any) => {
      if (visible) {
        setTimeout(() => (searchInput.current as any)?.select());
      }
    },
    render: (text: any, record: any) => {
      if (options.render) {
        return options.render(text, record);
      }
      let searchWords = [searchText];
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

  const handleColumnSearch = (selectedKeys: any, confirm: any) => {
    confirm();
    setPagination(Object.assign({}, pagination, { current: 1 }));
    setGlobSearchCurrent("");
    setGlobSearch("");
    setSearchText(selectedKeys[0]);
  };

  const handleReset = (clearFilters: any) => {
    clearFilters();
    setSearchText("");
  };

  const onAdvancedSearchChangeLabel = (i: number, e: any) => {
    advancedFields[i][0] = e.target.value;
    setAdvancedFields([...advancedFields]);
  };

  const onAdvancedSearchChange = (i: number, e: any) => {
    advancedFields[i][1] = e.target.value;
    setAdvancedFields([...advancedFields]);
  };

  const onAdvancedSearchAdd = () => {
    setAdvancedFields([...advancedFields, ["", ""]]);
  };

  const onAdvancedSearchRemove = (i: number) => {
    advancedFields.splice(i, 1);
    setAdvancedFields([...advancedFields]);
  };

  const onAdvancedSearch = () => {
    setSearchText("");
    setGlobSearchCurrent("");
    setGlobSearch("");
    setShowAdvanced(false);
    let so: any = {};
    for (let f of advancedFields) {
      if (!f[0].length || !f[1].length) continue;
      so[f[0]] = [f[1]];
    }
    navigate(encodeUrl(so));
  };

  const columns: ColumnType<any>[] = [
    {
      title: "ID",
      dataIndex: "id",
      render: (text: any, record: any) => (
        <Link to={"/files/" + record.id}>{text}</Link>
      ),
    },
    {
      title: "Patient ID",
      dataIndex: "Patient ID",
      ...getColumnSearchProps("Patient ID", {
        render: (text: any, record: any) => (
          <Link to={"/patients/" + record.patient_db_id}>{text}</Link>
        ),
      }),
    },
    {
      title: "Patient Name",
      dataIndex: "Patient's Name",
      ...getColumnSearchProps("Patient's Name"),
    },
    {
      title: "Study ID",
      dataIndex: "Study ID",
      ...getColumnSearchProps("Study ID"),
    },
    {
      title: "Study Description",
      dataIndex: "Study Description",
      ...getColumnSearchProps("Study Description"),
    },
    {
      title: "Series Number",
      dataIndex: "Series Number",
      ...getColumnSearchProps("Series Number"),
    },
    {
      title: "Series Description",
      dataIndex: "Series Description",
      ...getColumnSearchProps("Series Description"),
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
    onChange: (selectedRowKeys: any, selectedRows: any) => {
      setSelected(selectedRowKeys);
    },
    getCheckboxProps: (record: any) => ({
      disabled: false,
      name: record.name,
    }),
  };

  return (
    <Content className="files">
      <Row>
        <Col span={16}>
          <Search
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
      <Button
        style={{ marginBottom: "10px" }}
        type="primary"
        onClick={() => setShowUpload(true)}
      >
        Upload
      </Button>
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
      <PageState
        error={error}
        onRetry={() => fetch()}
        empty={!loading && !error && data.length === 0}
        emptyMessage={
          globSearch || searchText
            ? "No files match your search"
            : "No files uploaded"
        }
      >
        {isMobile ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.map((item: any, idx: number) => (
              <Card
                key={item.id}
                className="stagger-enter"
                size="small"
                hoverable
                onClick={() => navigate(`/files/${item.id}`)}
                style={
                  {
                    cursor: "pointer",
                    "--stagger-index": idx,
                  } as React.CSSProperties
                }
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>
                      {item["Patient ID"] || item.id}
                    </div>
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
          </div>
        ) : (
          <Table
            className="filesTable"
            scroll={{ x: 500 }}
            columns={columns}
            rowKey={(record: any) => record.id}
            dataSource={data}
            rowSelection={rowSelection}
            pagination={pagination}
            loading={loading}
            onChange={handleTableChange}
            rowClassName={() => "stagger-enter"}
            onRow={(_: any, index?: number) => ({
              style: { "--stagger-index": index ?? 0 } as React.CSSProperties,
            })}
          />
        )}
      </PageState>
    </Content>
  );
}

export default withSidebar(Files);
