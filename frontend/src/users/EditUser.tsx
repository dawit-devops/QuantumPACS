import React, { useState, useEffect } from "react";
import {
  App,
  Button,
  Modal,
  Form,
  Input,
  Checkbox,
  Select,
  Space,
  Typography,
} from "antd";
import { CopyOutlined } from "@ant-design/icons";
import { createUser } from "../api/users";
import { listRoles } from "../api/roles";
import { listSessionTenants } from "../api/tenants";
import { useAuth } from "../auth/AuthContext";

const { Text, Paragraph } = Typography;

export function AddUserFinish(props: any) {
  const { message } = App.useApp();
  const copyPassword = () => {
    navigator.clipboard.writeText(props.password);
    message.success("Password copied to clipboard");
  };

  return (
    <Modal
      open={props.visible}
      title="User Created"
      okText="Done"
      onOk={props.onClose}
      onCancel={props.onClose}
    >
      <div style={{ marginBottom: 16 }}>
        <Text strong>Username:</Text>
        <Paragraph copyable style={{ margin: "4px 0 0", fontSize: 16 }}>
          {props.username}
        </Paragraph>
      </div>
      <div>
        <Text strong>Password:</Text>
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            marginTop: 4,
          }}
        >
          <code
            style={{
              fontSize: 16,
              background: "#f5f5f5",
              padding: "4px 8px",
              borderRadius: 4,
            }}
          >
            {props.password}
          </code>
          <Button size="small" icon={<CopyOutlined />} onClick={copyPassword}>
            Copy
          </Button>
        </div>
      </div>
      <Text
        type="secondary"
        style={{ display: "block", marginTop: 12, fontSize: 12 }}
      >
        Share these credentials with the user. The password will not be shown
        again.
      </Text>
    </Modal>
  );
}

export function AddUser(props: any) {
  const { message } = App.useApp();
  const { hasPermission, user } = useAuth();
  const [visible, setVisible] = useState(false);
  const [result, setResult] = useState<any>({});
  const [roles, setRoles] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [form] = Form.useForm();

  // Tenant assignment is a platform-admin capability: only users holding
  // TENANT_READ may scope a new user to a tenant via the form.
  const canAssignTenant = hasPermission("TENANT_READ");

  // The Admin flag is a second super-admin channel (backend users.py:240
  // rejects it unless request.user.admin): only platform admins may grant it,
  // so the checkbox is hidden for everyone else — same contract as the API.
  const canGrantAdmin = user?.admin === true;

  useEffect(() => {
    if (visible) {
      listRoles()
        .then(setRoles)
        .catch(() => {});
      if (canAssignTenant) {
        listSessionTenants()
          .then(setTenants)
          .catch(() => {});
      }
    }
  }, [visible, canAssignTenant]);

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
          const data: any = {
            username: values.username,
            admin: canGrantAdmin ? values.admin || false : false,
          };
          if (values.role_id) data.role_id = values.role_id;
          if (values.tenant) data.tenant = values.tenant;
        createUser(data)
          .then((res: any) => {
            form.resetFields();
            setVisible(false);
            setResult({ password: res.password, username: res.username });
          })
          .catch((e: any) => {
            message.error(e.message);
          });
      })
      .catch(() => {});
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
      />
      <Modal
        title="Add user"
        okText="Add"
        open={visible}
        onCancel={handleCancel}
        onOk={handleCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: "Please enter username!" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="role_id" label="Role">
            <Select
              allowClear
              placeholder="Select a role"
              options={roles.map((r: any) => ({
                value: r.id,
                label: `${r.name} (${r.slug})`,
              }))}
            />
          </Form.Item>
          {canAssignTenant && (
            <Form.Item name="tenant" label="Tenant">
              <Select
                allowClear
                placeholder="Platform-wide user (no tenant)"
                options={tenants.map((t: any) => ({
                  value: t.slug,
                  label: t.name,
                }))}
              />
            </Form.Item>
          )}
          {canGrantAdmin && (
            <Form.Item name="admin" valuePropName="checked" initialValue={false}>
              <Checkbox>Admin</Checkbox>
            </Form.Item>
          )}
          {!canGrantAdmin && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              Platform admin access is reserved for platform administrators.
            </Text>
          )}
        </Form>
      </Modal>
    </div>
  );
}
