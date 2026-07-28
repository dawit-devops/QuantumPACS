import React, { Suspense, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import withRouter from '../withRouter';
import { Layout, message, Menu, Breadcrumb, Grid, Spin } from 'antd';
import { EyeOutlined, TableOutlined, ShareAltOutlined, HistoryOutlined, LockOutlined } from '@ant-design/icons';
import withSidebar from '../common/base';

const { useBreakpoint } = Grid;
import { request } from '../helpers';
import { wadoRsUrl } from '../dicomweb/dicomweb';
import { useAuth } from '../auth/AuthContext';
import { API_URL } from '../config';
const CornerstoneElement = React.lazy(() => import('./CornerstoneElement'));
import EditableTable from './EditableTable';
import Changes from './Changes';
import Share from './Share';
import Management from './Management';
import './Detail.css';

const Content = Layout.Content;

function wrap(txt: string) {
  if (!txt) return '';
  return `(${txt})`;
}

function Detail(props: any) {
  document.title = 'QuantumPACS - Detail';
  const imagePath = `wadouri:${API_URL}/files/${props.match.params.id}/data`;
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const { hasPermission } = useAuth();

  let [tab, setTab] = useState('image');
  let [data, setData] = useState<any>({});
  let [loading, setLoading] = useState(false);
  let [key, setKey] = useState(1);
  let [study, setStudy] = useState<any>(null);
  let [series, setSeries] = useState<any>(null);
  let [image, setImage] = useState(imagePath);
  let [wadoRsImage, setWadoRsImage] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    let params = props.match.params;

    setImage(`wadouri:${API_URL}/files/${params.id}/data`);

    request(`files/${params.id}`).then((data: any) => {
      const meta = data?.meta || {};
      if (meta.study_instance_uid && meta.series_instance_uid && meta.sop_instance_uid) {
        setWadoRsImage(wadoRsUrl(meta.study_instance_uid, meta.series_instance_uid, meta.sop_instance_uid));
      }
      setLoading(false);
      for (let s of data.patient.studies) {
        if (s.id === data.study_db_id) {
          setStudy(s);
          for (let sr of s.series) {
            if (sr.id === data.series_db_id) {
              setSeries(sr);
            }
          }
        }
      }
      setData(data);

      // hack to trigger re-render, to help cornerstone initialization
      if (!(window as any).ctinit) {
        (window as any).ctinit = true;
        setTimeout(() => {
          setKey(2);
        }, 500);
      }

    }).catch((e: any) => {
      setLoading(false);
      let msg = 'File fail to load';
      if (e.message === '404') {
        msg = 'File not found';
      }
      message.error(msg);
      if (e.message === '404') {
        props.history.push('/');
      }
    });
    // eslint-disable-next-line
  }, [props.match.params.id]);

  const background = tab === 'image' ? '#000' : '';

  const changeStudy = (e: any, s: any) => {
    e.preventDefault();
    setStudy(s);
    setSeries(s.series[0]);
  };

  const studiesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.study_id,
      label: <a href="" onClick={(e: any) => changeStudy(e, d)}>{`Study ${d.study_id} ${wrap(d.description)}`}</a>,
    }));
  };

  const changeSeries = (e: any, s: any) => {
    e.preventDefault();
    setSeries(s);
  };

  const seriesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.number,
      label: <a href='' onClick={(e: any) => changeSeries(e, d)}>{`Series ${d.number} ${wrap(d.description)}`}</a>,
    }));
  };

  const filesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.id,
      label: <Link to={`/files/${d.id}`}>{`File ${d.name}`}</Link>,
    }));
  };

  const tempKey = localStorage.getItem('tempKey');

  return (
    <Content style={{
      alignItems: 'center',
      justifyContent: 'center',
      background: background,
    }}>
      <Menu style={{ paddingLeft: '40px' }} defaultSelectedKeys={[tab]} mode="horizontal">
        <Menu.Item key="image" onClick={() => setTab('image')} >
          <EyeOutlined />
          Image
        </Menu.Item>
        <Menu.Item key="data" onClick={() => setTab('data')} >
          <TableOutlined />
          Data
        </Menu.Item>
        {
          !tempKey &&
          <Menu.Item key="share" onClick={() => setTab('share')} >
            <ShareAltOutlined />
            Share
          </Menu.Item>
        }
        {
          !tempKey &&
          <Menu.Item key="changes" onClick={() => setTab('changes')} >
            <HistoryOutlined />
            Changes
          </Menu.Item>
        }
        {
          !tempKey && hasPermission('USER_ADMIN') &&
          <Menu.Item key="admin" onClick={() => setTab('admin')} >
            <LockOutlined />
            Admin
          </Menu.Item>
        }
      </Menu>
      {
        data && data.patient && ['image'].includes(tab) &&
        <Breadcrumb style={{ background: '#fff', padding: '5px' }}>
          <Breadcrumb.Item>
            <Link to={`/patients/${data.patient_id}`}>
              {isMobile ? data.patient.name : `${data.patient.name} (${data.patient.patient_id})`}
            </Link>
          </Breadcrumb.Item>
          <Breadcrumb.Item menu={{ items: studiesDrop(data.patient.studies) }}>
            {isMobile ? `S:${study?.study_id}` : `Study ${study?.study_id} ${wrap(study?.description)}`}
          </Breadcrumb.Item>
          <Breadcrumb.Item menu={{ items: seriesDrop(study?.series) }}>
            {isMobile ? `Ser:${series?.number}` : `Series ${series?.number} ${wrap(series?.description)}`}
          </Breadcrumb.Item>
          <Breadcrumb.Item menu={{ items: filesDrop(series?.files) }}>
            {isMobile ? data.name : `File ${data.name}`}
          </Breadcrumb.Item>
        </Breadcrumb>
      }
      <Suspense fallback={<Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />}>
        <CornerstoneElement key={key}
          file={data}
          files={series?.files || null}
          changeFile={(v: number) => props.history.push(`/files/${series?.files[v].id}`)}
          image={image}
          wadoRsImage={wadoRsImage}
          visible={tab === 'image'}
        />
      </Suspense>
      <EditableTable
        style={tab !== 'data' ? { display: 'none' } : {}}
        rowKey={(record: any) => record.key}
        pagination={{ pageSize: 20 }}
        file={data}
        loading={loading}
      />
      {tab === 'changes' && <Changes file={data}></Changes>}
      {tab === 'share' && <Share file={data}></Share>}
{tab === 'admin' && hasPermission('USER_ADMIN') && <Management file={data}></Management>}
    </Content>
  );
}

export default withSidebar(withRouter(Detail));
