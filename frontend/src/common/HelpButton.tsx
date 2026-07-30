import React, { useState } from 'react';
import { Button, Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { QuickReference } from './QuickReference';

export function HelpButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Tooltip title="Help & shortcuts" placement="left">
        <Button
          type="primary"
          shape="circle"
          icon={<QuestionCircleOutlined />}
          onClick={() => setOpen(true)}
          aria-label="Open help and shortcuts reference"
          style={{
            position: 'fixed', bottom: 80, right: 20, zIndex: 900,
            width: 44, height: 44,
            boxShadow: 'var(--shadow-md)',
          }}
        />
      </Tooltip>
      <QuickReference open={open} onClose={() => setOpen(false)} />
    </>
  );
}
