import React from 'react';
import { Button, Modal, Row, Col, Input } from 'antd';
import { CloseOutlined } from '@ant-design/icons';

export default function AdvancedSearch(props: any) {
  return (
    <Modal
      open={props.visible}
      title="Search"
      okText="Search"
      onCancel={props.onClose}
      onOk={() => props.onSearch()}
    >
      {props.fields.map((f: any, i: number) => (
        <Row key={i} style={{ paddingBottom: '5px' }}>
          <Col span={12} style={{ paddingRight: '5px' }}>
            {
              i < props.fixed ?
                <span>{f[0]}</span> :
                <Input value={f[0]} onChange={(e: any) => props.onChangeLabel(i, e)}></Input>
            }
          </Col>
          <Col span={10} style={{ paddingRight: '5px' }} >
            <Input value={f[1]} onChange={(e: any) => props.onChange(i, e)}></Input>
          </Col>
          <Col span={2}>
            {
              i >= props.fixed &&
              <Button icon={<CloseOutlined />} onClick={() => props.onRemove(i)}></Button>
            }
          </Col>
        </Row>
      ))}
      <Button type='primary' onClick={() => props.onAdd()}>Add</Button>
    </Modal>
  );
}
