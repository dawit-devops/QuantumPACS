import { useDocumentTitle } from "../hooks";
import React, { useState } from "react";
import withRouter from "../withRouter";
import { Button, message, Layout, Modal } from "antd";
import { deleteFile } from "../api/files";
const { Content } = Layout;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function Management(props: any) {
  useDocumentTitle("QuantumPACS - Management");
  let [loading, setLoading] = useState(false);

  const confirmDelete = () => {
    Modal.confirm({
      title: "Delete this file?",
      content:
        "This will permanently remove the file from all storage backends. This action cannot be undone.",
      okText: "Delete",
      okType: "danger",
      cancelText: "Cancel",
      onOk: () => {
        setLoading(true);
        return deleteFile(props.file.id)
          .then(() => sleep(1000))
          .then(() => props.history.push("/"))
          .catch(() => message.error("Deletion failed"))
          .finally(() => setLoading(false));
      },
    });
  };

  return (
    <Content
      style={{ padding: 24, background: "#fff", minHeight: 360, maxWidth: 600 }}
    >
      <Button
        size="large"
        type={"danger" as any}
        onClick={confirmDelete}
        disabled={loading}
      >
        {loading ? "Deleting..." : "Delete"}
      </Button>
    </Content>
  );
}

export default withRouter(Management);
