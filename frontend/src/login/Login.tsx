import React, { useEffect } from 'react';
import withRouter from '../withRouter';
import { useFetch } from '../hooks';
import { Form, Input, Button, message, Layout, Card, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import QuantumLogo from '../common/QuantumLogo';
import './Login.css';
const { Content } = Layout;
const { Text } = Typography;


function LoginForm(props: any) {
  document.title = 'QuantumPACS - Login';

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
      'height': '100%',
      background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)',
    }}
    >
      <Content>
        <Card
          style={{ width: 380, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}
          styles={{ body: { padding: '40px 32px' } }}
        >
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <QuantumLogo size={48} />
          </div>
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 24, fontSize: 13 }}>
            Sign in to your account
          </Text>
          <Form form={form} onFinish={handleSubmit} className="login-form">
            <Form.Item name="username" rules={[{ required: true, message: 'Please input your username!' }]}>
              <Input
                prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                placeholder="Username"
                size="large"
              />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: 'Please input your password!' }]}>
              <Input.Password
                prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                placeholder="Password"
                size="large"
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" className="login-form-button"
                size="large" loading={showLoading}>
                  Sign In
              </Button>
            </Form.Item>
          </Form>
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', fontSize: 11, marginTop: 16 }}>
            QuantumPACS v1.0 — Diagnostic Clarity, Quantum Fast
          </Text>
        </Card>
      </Content>
    </ Layout>
  );
}


export default withRouter(LoginForm);
