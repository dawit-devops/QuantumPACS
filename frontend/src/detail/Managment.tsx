import React, { useState } from 'react';
import withRouter from '../withRouter';
import { Button, message, Layout, Modal } from 'antd';
import { request } from '../helpers';
const { Content } = Layout;

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function Managment(props: any) {
  document.title = 'QuantumPACS - Managment';
  let [loading, setLoading] = useState(false);

  const confirmDelete = () => {
    Modal.confirm({
      title: 'Delete this file?',
      content: 'This will permanently remove the file from all storage backends. This action cannot be undone.',
      okText: 'Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: () => {
        setLoading(true);
        return request(`files/${props.file.id}`, { method: 'DELETE' })
          .then(() => sleep(1000))
          .then(() => props.history.push('/'))
          .catch(() => message.error('Deletion failed'))
          .finally(() => setLoading(false));
      },
    });
  };

  return (
    <Content style={{ padding: 24, background: '#fff', minHeight: 360, maxWidth: 600 }}>
      <Button size="large" type={'danger' as any} onClick={confirmDelete} disabled={loading}>
        {loading ? 'Deleting...' : 'Delete'}
      </Button>
    </Content>
  );
}

export default withRouter(Managment);
