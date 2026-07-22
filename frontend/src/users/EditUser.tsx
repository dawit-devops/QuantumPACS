import React, { useState } from 'react';
import { Button, Modal, Form, Input, Checkbox, message } from 'antd';
import { request } from '../helpers';

export function AddUserFinish(props: any) {
  return (
    <Modal
      open={props.visible}
      title="New user"
      okText="Ok"
      onCancel={props.onClose}
      footer={null}
    >
      <p>Username: {props.username}</p>
      <p>Password: {props.password}</p>
    </Modal>
  );
}

export function AddUser(props: any) {
  let [visible, setVisible] = useState(false);
  let [result, setResult] = useState<any>({});
  const [form] = Form.useForm();

  const showModal = () => {
    setVisible(true);
  };

  const handleCancel = () => {
    setVisible(false);
  };

  const handleCreate = () => {
    form.validateFields().then((values: any) => {
      request('users', { data: values }).then((data: any) => {
        form.resetFields();
        setVisible(false);
        setResult({password: data.password, username: data.username});
      }).catch((e: any) => {
        message.error(e.message);
      });
    }).catch(() => {});
  };

  const closeResult = () => {
    setResult({});
    props.reload();
  };

  return (
    <div style={props.style}>
      <Button type="primary" onClick={showModal}>
        Add user
      </Button>
      <AddUserFinish
        visible={result.password}
        password={result.password}
        username={result.username}
        onClose={closeResult}
      ></AddUserFinish>
      <Modal
        title="Add user"
        okText="Add"
        open={visible}
        onCancel={handleCancel}
        onOk={handleCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="Username" rules={[{ required: true, message: 'Please enter username!' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="admin" valuePropName="checked" initialValue={false}>
            <Checkbox>Admin</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
