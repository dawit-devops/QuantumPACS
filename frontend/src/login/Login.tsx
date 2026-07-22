import React, { useEffect } from 'react';
import withRouter from '../withRouter';
import { useFetch } from '../hooks';
import { Form, Input, Button, message, Layout } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import './Login.css';
const { Content } = Layout;


function LoginForm(props: any) {
  document.title = 'Login';

  const [form] = Form.useForm();
  const { exec, showLoading, loading, data, error } = useFetch('login');

  useEffect(() => {
    if (!data) return;
    localStorage.setItem('userId', data.id);
    localStorage.setItem('admin', data.admin);
    localStorage.setItem('token', data.token);
    props.history.push('/');
  }, [data]);

  useEffect(() => {
    if (!loading && error) {
      message.error(error.error || error);
    }
  }, [loading, error]);

  const handleSubmit = (values: any) => {
    exec(
      true,
      {
        method: 'POST',
        body: JSON.stringify({ username: values.username, password: values.password }),
      }
    );
  };
  return (
    <Layout style={{
      'alignItems': 'center',
      'justifyContent': 'center',
      'height': '100%'
    }}
    >
      <Content style={{ 'marginTop': '200px' }}>
        <Form form={form} onFinish={handleSubmit} className="login-form">
          <h1 style={{ 'fontSize': '32px', 'textAlign': 'center' }}>OpenPACS</h1>
          <Form.Item name="username" rules={[{ required: true, message: 'Please input your username!' }]}>
            <Input
              prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
              placeholder="Username"
            />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: 'Please input your password!' }]}>
            <Input
              prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
              type="password"
              placeholder="Password"
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" className="login-form-button"
              loading={showLoading}>
                Login
            </Button>
          </Form.Item>
        </Form>
      </Content>
    </ Layout>
  );
}


export default withRouter(LoginForm);
