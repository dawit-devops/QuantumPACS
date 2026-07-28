import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import withRouter from '../withRouter';
import Highlighter from 'react-highlight-words';
import { Layout, Table, Input, message, Button, Row, Col } from 'antd';
import type { InputRef } from 'antd';
import type { ColumnType } from 'antd/es/table';
import { SearchOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';
import { request, open } from '../helpers';
import { AdminFiles } from './AdminFiles';
import AdvancedSearch from './AdvancedSearch';
import { PAGINATION } from '../config';
import './Files.css';

const Content = Layout.Content;
const Search = Input.Search;

function encodeUrl(obj: any) {
  return '?' + encodeURIComponent(JSON.stringify(obj));
}

function decodeUrl(url: string) {
  if (!url.length) return {};
  return JSON.parse(decodeURIComponent(url.slice(1)));
}

const initialAdvancedFields = [
  ['Patient ID', ''],
  ['Patient\'s Name', ''],
  ['Patient\'s Age', ''],
  ['Patient\'s Gender', ''],
  ['Study ID', ''],
  ['Study Description', ''],
  ['Series Number', ''],
  ['Series Modality', ''],
  ['Series Description', ''],
  ['Referring Physician\'s Name', ''],
  ['Performing Physician\'s Name', ''],
  ['SOP Class UID', ''],
];

function extractDicomValue(tag: any): string {
  if (!tag || !tag.Value) return '';
  if (typeof tag.Value[0] === 'object') {
    return tag.Value.map((v: any) => v.Alphabetic || v.Value || '').join(' ');
  }
  return tag.Value.join(' ');
}

function dicomJsonToFlat(studies: any[]): any[] {
  return studies.map((s: any) => ({
    id: extractDicomValue(s['0020000D']),
    'Patient ID': extractDicomValue(s['00100020']),
    'Patient\'s Name': extractDicomValue(s['00100010']),
    'Study ID': extractDicomValue(s['0020000D']),
    'Study Description': extractDicomValue(s['00081030']),
    'Modality': extractDicomValue(s['00080060']),
    'Accession Number': extractDicomValue(s['00080050']),
  }));
}

function searchToQidoParams(searchObj: any): Record<string, string> {
  const params: Record<string, string> = {};
  const fieldMap: Record<string, string> = {
    'Patient ID': 'PatientID',
    'Study ID': 'StudyInstanceUID',
    'Accession Number': 'AccessionNumber',
    'Modality': 'Modality',
    'query': 'PatientID',
  };
  for (const [field, value] of Object.entries(searchObj)) {
    if (field in fieldMap && value && String(value).trim()) {
      params[fieldMap[field]] = String(value).trim();
    }
  }
  return params;
}

function Files(props: any) {

  let [data, setData] = useState<any[]>([]);
  let [pagination, setPagination] = useState<any>({ pageSize: PAGINATION.limit });
  let [loading, setLoading] = useState(false);
  let [showUpload, setShowUpload] = useState(false);
  let [showAdvanced, setShowAdvanced] = useState(false);
  let searchInput = useRef<InputRef>(null);
  let [globSearchCurrent, setGlobSearchCurrent] = useState('');
  let [globSearch, setGlobSearch] = useState('');
  let [searchText, setSearchText] = useState('');
  let [advancedFields, setAdvancedFields] = useState(initialAdvancedFields.map(e => [...e]));
  let [selected, setSelected] = useState<any[]>([]);

  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    const pager = { ...pagination };
    pager.current = pagination.current;
    setPagination(Object.assign({}, pagination, { current: pagination.current }));
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
    props.history.push(encodeUrl(s));
  };

  useEffect(() => {
    fetch();
    // eslint-disable-next-line
  }, [window.location.search]);

  useEffect(() => {
    setPagination(Object.assign({}, pagination, { pageSize: PAGINATION.limit }));
    fetch();
    // eslint-disable-next-line
  }, [PAGINATION.limit]);

   const fetchQidoResults = (qidoParams: Record<string, string>): Promise<any[]> => {
     return request('v2/dicomweb/studies', { query: qidoParams }).then((res: any) => {
       const results = Array.isArray(res) ? res : (res.data || []);
       return dicomJsonToFlat(results);
     });
   };

   const fetch = () => {
     setLoading(true);
     const searchObj = decodeUrl(window.location.search);
     if (searchObj.query) {
       setGlobSearch(searchObj.query);
       setSearchText('');
     } else {
       let set = false;
       for (let k in searchObj) {
         if (Array.isArray(searchObj[k])) {
           setSearchText(searchObj[k][0]);
           setGlobSearch('');
           set = true;
         }
       }
       if (!set) {
         setGlobSearch('');
         setSearchText('');
       }
     }
     const qidoParams = searchToQidoParams(searchObj);
     const hasQidoParams = Object.keys(qidoParams).length > 0;
     if (hasQidoParams) {
       fetchQidoResults(qidoParams).then((results: any[]) => {
         setLoading(false);
         if (results.length > 0) {
           setData(results);
           setPagination(Object.assign({}, pagination, { total: results.length }));
           return;
         }
         fallbackToV2(searchObj);
       }).catch(() => {
         fallbackToV2(searchObj);
       });
     } else {
       fallbackToV2(searchObj);
     }
   };

   const fallbackToV2 = (searchObj: any) => {
     request('files', { data: searchObj }).then((data: any) => {
       setLoading(false);
       setData(data.data);
       setPagination(Object.assign({}, pagination, { total: data.total }));
     }).catch((e: any) => {
       setLoading(false);
       message.error(e.message);
     });
   };

  const downloadFiles = () => {
    if (!selected || !selected.length) return;

    open('files/download.zip?ids=' + selected.join(','))
      .catch(() => {
        message.error('Fail to download');
      });
  };

  const downloadData = () => {
    if (!selected || !selected.length) return;

    open('files/download.csv?ids=' + selected.join(','))
      .catch(() => {
        message.error('Fail to download');
      });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPagination(Object.assign({}, pagination, { current: 1 }));
    setGlobSearchCurrent(e.target.value);
  };

  const handleSearch = (value: string) => {
    setAdvancedFields(initialAdvancedFields.map(e => [...e]));
    setSearchText('');
    setGlobSearch(value);
    if (value) {
      props.history.push(encodeUrl({ query: value }));
    } else {
      props.history.push('');
    }
  };

  const getColumnSearchProps = (dataIndex: string, options: any = {}): ColumnType<any> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: any) => (
      <div style={{ padding: 8 }}>
        <Input
          ref={node => {
            (searchInput as any).current = node;
          }}
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e: any) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleColumnSearch(selectedKeys, confirm)}
          style={{ width: 188, marginBottom: 8, display: 'block' }}
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
        <Button onClick={() => handleReset(clearFilters)} size="small" style={{ width: 90 }}>
          Reset
        </Button>
      </div>
    ),
    filterIcon: (filtered: any) => (
      <SearchOutlined style={{ color: filtered ? 'var(--color-blue-500)' : undefined }} />
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
          highlightStyle={{ backgroundColor: 'var(--table-highlight-bg)', padding: 0 }}
          searchWords={searchWords}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      );
    },
  });

  const handleColumnSearch = (selectedKeys: any, confirm: any) => {
    confirm();
    setPagination(Object.assign({}, pagination, { current: 1 }));
    setGlobSearchCurrent('');
    setGlobSearch('');
    setSearchText(selectedKeys[0]);
  };

  const handleReset = (clearFilters: any) => {
    clearFilters();
    setSearchText('');
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
    setAdvancedFields([...advancedFields, ['', '']]);
  };

  const onAdvancedSearchRemove = (i: number) => {
    advancedFields.splice(i, 1);
    setAdvancedFields([...advancedFields]);
  };

  const onAdvancedSearch = () => {
    setSearchText('');
    setGlobSearchCurrent('');
    setGlobSearch('');
    setShowAdvanced(false);
    let so: any = {};
    for (let f of advancedFields) {
      if (!f[0].length || !f[1].length) continue;
      so[f[0]] = [f[1]];
    }
    props.history.push(encodeUrl(so));
  };

  const columns: ColumnType<any>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      render: (text: any, record: any) => <Link to={'/files/' + record.id}>{text}</Link>,
    },
    {
      title: 'Patient ID',
      dataIndex: 'Patient ID',
      ...getColumnSearchProps('Patient ID', {
        render: (text: any, record: any) => <Link to={'/patients/' + record.patient_db_id}>{text}</Link>
      }),
    },
    {
      title: 'Patient Name',
      dataIndex: 'Patient\'s Name',
      ...getColumnSearchProps('Patient\'s Name'),
    },
    {
      title: 'Study ID',
      dataIndex: 'Study ID',
      ...getColumnSearchProps('Study ID'),
    },
    {
      title: 'Study Description',
      dataIndex: 'Study Description',
      ...getColumnSearchProps('Study Description'),
    },
    {
      title: 'Series Number',
      dataIndex: 'Series Number',
      ...getColumnSearchProps('Series Number'),
    },
    {
      title: 'Series Description',
      dataIndex: 'Series Description',
      ...getColumnSearchProps('Series Description'),
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
              marginBottom: 10
            }}
            value={globSearchCurrent}
            onChange={handleSearchChange}
          />
        </Col>
        <Col span={8}>
          <Button
            size='large' type='primary'
            onClick={() => setShowAdvanced(true)}
          >
            Advanced
          </Button>
        </Col>
      </Row>
      <Button style={{ marginBottom: '10px' }} type="primary"
        onClick={() => setShowUpload(true)}>
        Upload
      </Button>
      <Button style={{ marginBottom: '10px', marginLeft: '5px' }} type="primary"
        onClick={() => downloadFiles()}>
        Download files
      </Button>
      <Button style={{ marginBottom: '10px', marginLeft: '5px' }} type="primary"
        onClick={() => downloadData()}>
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
        onClose={() => {
          fetch();
          setShowUpload(false);
        }}>
      </AdminFiles>
      <Table
        className='filesTable'
        scroll={{ x: 500 }}
        columns={columns}
        rowKey={(record: any) => record.id}
        dataSource={data}
        rowSelection={rowSelection}
        pagination={pagination}
        loading={loading}
        onChange={handleTableChange}
      />
    </Content>
  );
}

export default withRouter(withSidebar(Files));
