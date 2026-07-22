import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { unstable_HistoryRouter as Router } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { createRoot } from 'react-dom/client';
import Login from './login/Login';
import Account from './account/Account';
import Replicas from './replicas/Replicas';
import Users from './users/Users';
import Logs from './logs/Logs';
import NotFound from './notfound/NotFound';
import Patient from './patient/Patient';
import Files from './files/Files';
import Detail from './detail/Detail';
import history from './history';
import { init } from './ws';

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const authed = localStorage.getItem('userId') || localStorage.getItem('tempKey');
  if (!authed) {
    return <Navigate to="/login" replace />;
  }
  return children;
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
    <ConfigProvider>
      <Router history={history as any}>
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
      </Router>
    </ConfigProvider>
    );
  }

const rootEl = document.getElementById('root')!;
createRoot(rootEl).render(<App />);
