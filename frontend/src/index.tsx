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

function App() {
  const params = new URLSearchParams(window.location.search);
  const tempKey = params.get('key');

  if (tempKey) {
    localStorage.setItem('tempKey', tempKey);
  }
  useEffect(() => {
    init();
  }, []);

  const authed = localStorage.getItem('userId') || localStorage.getItem('tempKey');

  return (
    <ConfigProvider>
      <Router history={history as any}>
      {authed ? (
        <Routes>
          <Route path="/account" element={<Account />} />
          <Route path="/replicas" element={<Replicas />} />
          <Route path="/users" element={<Users />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/patients/:id" element={<Patient />} />
          <Route path="/files/:id" element={<Detail />} />
          <Route path="/" element={<Files />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      ) : (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      )}
      </Router>
    </ConfigProvider>
    );
  }

const rootEl = document.getElementById('root')!;
createRoot(rootEl).render(<App />);
