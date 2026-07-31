import React from 'react';
import { Button, Modal, Row, Col, Input } from 'antd';
import { CloseOutlined } from '@ant-design/icons';

export default function AdvancedSearch(props: any) {
  return (
    <Modal
      open={props.visible}
      title="Advanced Search"
      okText="Search"
      onCancel={props.onClose}
      onOk={() => props.onSearch()}
    >
      {props.fields.map((f: any, i: number) => (
        <Row key={i} style={{ paddingBottom: '5px' }}>
          <Col span={12} style={{ paddingRight: '5px' }}>
            {
              i < props.fixed ?
                <span id={`advanced-field-label-${i}`}>{f[0]}</span> :
                <Input
                  value={f[0]}
                  onChange={(e: any) => props.onChangeLabel(i, e)}
                  aria-label={`Field name ${i + 1}`}
                ></Input>
            }
          </Col>
          <Col span={10} style={{ paddingRight: '5px' }} >
            <Input
              value={f[1]}
              onChange={(e: any) => props.onChange(i, e)}
              aria-labelledby={i < props.fixed ? `advanced-field-label-${i}` : undefined}
              aria-label={i >= props.fixed ? `Field value ${i + 1}` : undefined}
            ></Input>
          </Col>
          <Col span={2}>
            {
              i >= props.fixed &&
              <Button icon={<CloseOutlined />} onClick={() => props.onRemove(i)} aria-label={`Remove field ${i + 1}`}></Button>
            }
          </Col>
        </Row>
      ))}
      <Button type='primary' onClick={() => props.onAdd()} aria-label="Add search field">Add</Button>
    </Modal>
  );
}
