import React, { useEffect } from 'react';
import withRouter from '../withRouter';
import { useFetch } from '../hooks';
import withSidebar from '../common/base';
import { Form, Input, Button, message, Layout } from 'antd';
import { LockOutlined } from '@ant-design/icons';
const { Content } = Layout;


function Account(props: any) {
  document.title = 'Account';

  const [form] = Form.useForm();
  const { exec, loading, data, error } = useFetch('change_password');

  useEffect(() => {
    if (!loading && error) {
      message.error(error.error || error);
    }
  }, [loading, error]);

  useEffect(() => {
    if (data && Object.keys(data).length === 0) {
      message.success('Password changed!');
    }
  }, [data]);

  const handleSubmit = (values: any) => {
    exec(
      true,
      {
        method: 'POST',
        body: JSON.stringify({ password: values.password }),
      }
    );
  };

  return (
    <Content style={{ padding: 24, background: '#fff', minHeight: 360, maxWidth: 600 }}>
      <Form form={form} onFinish={handleSubmit} className="change-password-form">
        <Form.Item name="password" rules={[{ required: true, message: 'Please input your password!' }]}>
          <Input
            prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
            type="password"
            placeholder="Password"
          />
        </Form.Item>
        <Form.Item name="password2" rules={[
          { required: true, message: 'Please repeat your new password!' },
          ({ getFieldValue }) => ({
            validator(_, value) {
              if (!value || getFieldValue('password') === value) {
                return Promise.resolve();
              }
              return Promise.reject(new Error('Password do not match!'));
            },
          }),
        ]}>
          <Input
            prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
            type="password"
            placeholder="Password repeated"
          />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" className="login-form-button"
            loading={loading}>
                Change password
          </Button>
        </Form.Item>
      </Form>
    </Content>
  );
}

export default withRouter(withSidebar(Account));
