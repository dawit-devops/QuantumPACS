import React from 'react';
import Sidebar from './Sidebar';
import { Layout } from 'antd';

function withSidebar(Comp: React.ComponentType<any>) {
  function wrapper(props: any) {
    const tempKey = localStorage.getItem('tempKey');
    return (
      <Layout style={{
        minHeight: '100vh',
      }}>
        {!tempKey && <Sidebar {...props} />}
        <Comp {...props} />
      </Layout>
    );
  }
  return wrapper;
}

export default withSidebar;