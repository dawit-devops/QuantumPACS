import React, { useState, useEffect } from 'react';
import { Upload, Button, Modal, Row, Col } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { API_URL } from '../config';
import { getAccessToken } from '../helpers';
import './AdminFiles.css';

export function AdminFiles(props: any) {
  let [fileList, setFileList] = useState<any[]>([]);

  const onChange = (info: any) => {
    let fileList = [...info.fileList];
    fileList = fileList.map((file: any) => {
      if (file.response) {
        file.url = file.response.url;
      }
      return file;
    });
    if (info.file.status === 'done') {
      fileList = fileList.filter((f: any) => f.name !== info.file.name);
    }
    setFileList(fileList);
  };

  useEffect(() => {
    setFileList([]);
  }, [props]);

  return (
    <Modal
      open={props.visible}
      title="Upload"
      okText="Upload"
      onCancel={props.onClose}
      onOk={props.onClose}
    >
      <Row>
        <Col span={8} >
          <Upload
            name="file"
            multiple={true}
            action={API_URL + '/files/upload'}
            headers={{
              'X-Auth-Pacs': getAccessToken() || '',
            }}
            onChange={onChange as any}
            fileList={fileList}
          >
            <Button icon={<UploadOutlined />}>
              Upload files
            </Button>
          </Upload>
        </Col>
        <Col span={8} id='upload_directory' >
          <Upload
            action={API_URL + '/files/upload'}
            headers={{
              'X-Auth-Pacs': getAccessToken() || '',
            }}
            onChange={onChange as any}
            fileList={fileList}
            directory
          >
            <Button icon={<UploadOutlined />}>
              Upload directory
            </Button>
          </Upload>
        </Col>
      </Row>
    </Modal>
  );
}
