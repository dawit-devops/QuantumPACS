import React, { useState, useEffect } from "react";
import { Button, Modal, Form, Input, Select, message, InputNumber } from "antd";
import { request } from "../helpers";

const Option = Select.Option;

const s3regions = [
  "eu-central-1",
  "eu-west-1",
  "eu-west-2",
  "eu-west-3",
  "eu-north-1",
  "us-east-2",
  "us-east-1",
  "us-west-2",
];

export function EditReplicaModal(props: any) {
  const { visible, onCancel, onCreate, title, okText } = props;
  const [form] = Form.useForm();
  const [type, setType] = useState("local");

  useEffect(() => {
    if (visible) {
      setType("local");
      form.resetFields();
    }
  }, [visible, form]);

  return (
    <Modal
      open={visible}
      title={title}
      okText={okText}
      onCancel={onCancel}
      onOk={onCreate}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="type" initialValue="local">
          <Select style={{ width: 150 }} onChange={setType}>
            <Option value="local">Local</Option>
            <Option value="s3">Amazon S3</Option>
            <Option value="b2">Backblaze B2</Option>
          </Select>
        </Form.Item>
        <Form.Item
          name="delay"
          label="Delay (in minutes)"
          initialValue={0}
          rules={[{ required: true, message: "Please replica's delay!" }]}
        >
          <InputNumber min={0} />
        </Form.Item>
        {type === "local" && (
          <Form.Item name="location" label="Location">
            <Input />
          </Form.Item>
        )}
        {type === "b2" && (
          <Form.Item
            name="app_key_id"
            label="App key id"
            rules={[{ required: true, message: "Please enter app key id!" }]}
          >
            <Input />
          </Form.Item>
        )}
        {type === "b2" && (
          <Form.Item
            name="app_key"
            label="App key"
            rules={[{ required: true, message: "Please enter app key!" }]}
          >
            <Input />
          </Form.Item>
        )}
        {type === "s3" && (
          <Form.Item name="location" label="Region" initialValue={s3regions[0]}>
            <Select style={{ width: 120 }} defaultActiveFirstOption={true}>
              {s3regions.map((r: string) => (
                <Option key={r} value={r}>
                  {r}
                </Option>
              ))}
            </Select>
          </Form.Item>
        )}
        {type === "s3" && (
          <Form.Item
            name="access_key_id"
            label="Access key id"
            rules={[{ required: true, message: "Please enter access key id!" }]}
          >
            <Input />
          </Form.Item>
        )}
        {type === "s3" && (
          <Form.Item
            name="secret_access_key"
            label="Secret access key"
            rules={[
              { required: true, message: "Please enter secret access key!" },
            ]}
          >
            <Input />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}

export function AddReplica(props: any) {
  let [visible, setVisible] = useState(false);
  const [form] = Form.useForm();

  const showModal = () => {
    setVisible(true);
  };

  const handleCancel = () => {
    setVisible(false);
  };

  const handleCreate = () => {
    form
      .validateFields()
      .then((values: any) => {
        request("replicas", { data: values })
          .then(() => {
            form.resetFields();
            setVisible(false);
          })
          .then(() => {
            props.reload();
          })
          .catch(() => {
            message.error("Replica addition failed");
          });
      })
      .catch(() => {});
  };

  return (
    <div style={props.style}>
      <Button type="primary" onClick={showModal}>
        Add replica
      </Button>
      <EditReplicaModal
        title="Add replica"
        okText="Add"
        open={visible}
        onCancel={handleCancel}
        onCreate={handleCreate}
      />
    </div>
  );
}
