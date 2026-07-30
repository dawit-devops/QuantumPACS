import { useEffect } from 'react';
import withRouter from '../withRouter';
import { Spin } from 'antd';


function ShareView(props: any) {
  useEffect(() => {
    const key = props.match.params.key;
    if (key) {
      localStorage.setItem('tempKey', key);
    }
    props.history.replace('/');
  }, [props.history, props.match.params.key]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Spin size="large" tip="Opening shared study..." />
    </div>
  );
}


export default withRouter(ShareView);
