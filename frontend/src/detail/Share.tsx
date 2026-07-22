import React, { useState } from 'react';
import withRouter from '../withRouter';
import {
  Form, Input, InputNumber, Button, message, Layout, Modal, Row, Col,
} from 'antd';
import { request } from '../helpers';
const { Content } = Layout;


function Share(props: any) {
  document.title = 'Share';
  let [loading, setLoading] = useState(false);
  let [key, setKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const handleSubmit = () => {
    setLoading(true);
    form.validateFields().then((values: any) => {
      request(`files/${props.file.id}/share`, { data: values })
        .then((data: any) => {
          setLoading(false);
          setKey(data.key);
        }).catch(() => {
          setLoading(false);
          message.error('Share failed');
        });
    }).catch(() => setLoading(false));
  };

  function copy() {
    const copyText = document.getElementById('key') as HTMLInputElement;

    copyText.select();
    copyText.setSelectionRange(0, 99999);

    document.execCommand('copy');
  }

  return (
    <Content style={{ padding: 24, background: '#fff', minHeight: 360, maxWidth: 600 }}>
      <Form form={form} onFinish={handleSubmit} className="share-form">
        <Form.Item name="duration" label="Duration (in hours)" rules={[{ required: true, message: 'Please duration!' }]}>
          <InputNumber />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" className="login-form-button"
            loading={loading}>
            Share
          </Button>
        </Form.Item>
      </Form>
      {
        key !== null &&
        <Modal
          open={key !== null}
          title='Link'
          footer={[]}
          onCancel={() => setKey(null)}
          onOk={() => setKey(null)}
        >
          <Row>
            <Col span={20}>
              <Input id='key' defaultValue={`${window.location.href}?key=${key}`} ></Input>
            </Col>
            <Col span={2}>
              <Button type="dashed" onClick={copy}>Copy</Button>
            </Col>
          </Row>
        </Modal>
      }
    </Content>
  );
}

export default withRouter(Share);
