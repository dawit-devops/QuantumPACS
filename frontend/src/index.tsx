import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import { createRoot } from 'react-dom/client';
import './common/tokens.css';
import './index.css';
import { init } from './ws';
import { setNavigator } from './navigator';
import { theme } from './common/theme';

const Login = React.lazy(() => import('./login/Login'));
const Account = React.lazy(() => import('./account/Account'));
const Replicas = React.lazy(() => import('./replicas/Replicas'));
const Users = React.lazy(() => import('./users/Users'));
const Logs = React.lazy(() => import('./logs/Logs'));
const Patient = React.lazy(() => import('./patient/Patient'));
const Files = React.lazy(() => import('./files/Files'));
const Detail = React.lazy(() => import('./detail/Detail'));
const NotFound = React.lazy(() => import('./notfound/NotFound'));

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const authed = localStorage.getItem('userId') || localStorage.getItem('tempKey');
  if (!authed) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function NavigatorSetter() {
  const navigate = useNavigate();
  useEffect(() => { setNavigator(navigate); }, [navigate]);
  return null;
}

function App() {
  const params = new URLSearchParams(window.location.search);
  const tempKey = params.get('key');

  if (tempKey) {
    localStorage.setItem('tempKey', tempKey);
  }
  useEffect(() => {
    init();
  }, []);

  return (
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <NavigatorSetter />
        <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
            <Route path="/replicas" element={<ProtectedRoute><Replicas /></ProtectedRoute>} />
            <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
            <Route path="/logs" element={<ProtectedRoute><Logs /></ProtectedRoute>} />
            <Route path="/patients/:id" element={<ProtectedRoute><Patient /></ProtectedRoute>} />
            <Route path="/files/:id" element={<ProtectedRoute><Detail /></ProtectedRoute>} />
            <Route path="/" element={<ProtectedRoute><Files /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ConfigProvider>
    );
  }

const rootEl = document.getElementById('root')!;
createRoot(rootEl).render(<App />);
