import React from 'react';
import { Layout, Grid } from 'antd';
import Sidebar from './Sidebar';
import MobileNav from './MobileNav';

const { useBreakpoint } = Grid;

function withSidebar(Comp: React.ComponentType<any>) {
  function wrapper(props: any) {
    const screens = useBreakpoint();
    const isMobile = !screens.lg;
    const tempKey = localStorage.getItem('tempKey');
    return (
      <Layout style={{
        minHeight: '100vh',
        paddingBottom: isMobile && !tempKey ? 56 : 0,
      }}>
        {!tempKey && <Sidebar {...props} />}
        <Comp {...props} />
        {isMobile && !tempKey && <MobileNav />}
      </Layout>
    );
  }
  return wrapper;
}

export default withSidebar;