import { Modal } from "antd";
import { UploadZone } from "./UploadZone";

export function AdminFiles(props: any) {
  return (
    <Modal
      open={props.visible}
      title="Upload DICOM Files"
      footer={null}
      onCancel={props.onClose}
      width={560}
    >
      <UploadZone reload={props.reload} />
    </Modal>
  );
}
