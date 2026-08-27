import { useDocumentTitle } from "../hooks";
import React, { useState, useEffect, useCallback } from "react";
import {
  App,
  Layout,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  Popconfirm,
} from "antd";
import { ReloadOutlined, PlusOutlined, BookOutlined, DeleteOutlined } from "@ant-design/icons";
import withSidebar from "../common/base";
import { PageState } from "../common/PageState";
import {
  listBookmarkCollections,
  createBookmarkCollection,
  listStudyBookmarks,
  createStudyBookmark,
  deleteStudyBookmark,
  type BookmarkCollection,
  type StudyBookmark,
} from "../api/ris";
import "./StudyBookmarks.css";

const Content = Layout.Content;

function StudyBookmarks() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Study Bookmarks");
  const [collections, setCollections] = useState<BookmarkCollection[]>([]);
  const [bookmarks, setBookmarks] = useState<StudyBookmark[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collectionFilter, setCollectionFilter] = useState<string | undefined>();
  const [collectionOpen, setCollectionOpen] = useState(false);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [collectionForm] = Form.useForm();
  const [bookmarkForm] = Form.useForm();

  const fetchCollections = useCallback(() => {
    listBookmarkCollections()
      .then((data) => setCollections(data || []))
      .catch(() => {});
  }, []);

  const fetchBookmarks = useCallback(() => {
    setLoading(true);
    setError(null);
    listStudyBookmarks({ collection_id: collectionFilter })
      .then((data) => {
        setLoading(false);
        setBookmarks(data || []);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
        message.error(e.message);
      });
  }, [message, collectionFilter]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  const handleCreateCollection = async (values: any) => {
    try {
      await createBookmarkCollection({
        name: values.name,
        description: values.description || "",
      });
      message.success("Collection created");
      setCollectionOpen(false);
      collectionForm.resetFields();
      fetchCollections();
    } catch (e: any) {
      message.error(e.message || "Create failed");
    }
  };

  const handleCreateBookmark = async (values: any) => {
    try {
      await createStudyBookmark({
        study_uid: values.study_uid,
        study_desc: values.study_desc || "",
        collection_id: values.collection_id || "",
        notes: values.notes || "",
      });
      message.success("Study bookmarked");
      setBookmarkOpen(false);
      bookmarkForm.resetFields();
      fetchBookmarks();
    } catch (e: any) {
      message.error(e.message || "Bookmark failed");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteStudyBookmark(id);
      message.success("Bookmark removed");
      fetchBookmarks();
    } catch (e: any) {
      message.error(e.message || "Delete failed");
    }
  };

  const collectionName = (id: string) => {
    const c = collections.find((c) => c.id === id);
    return c ? c.name : "";
  };

  const columns: any[] = [
    {
      title: "Study",
      dataIndex: "study_desc",
      width: "28%",
      render: (v: string, row: StudyBookmark) => (
        <span>
          <BookOutlined style={{ marginRight: 6 }} />
          {v || row.study_uid}
        </span>
      ),
    },
    {
      title: "Study UID",
      dataIndex: "study_uid",
      width: "24%",
      render: (v: string) => <code>{v}</code>,
    },
    {
      title: "Collection",
      dataIndex: "collection_id",
      width: "16%",
      render: (v: string) => (v ? <Tag color="blue">{collectionName(v)}</Tag> : <span>—</span>),
    },
    {
      title: "Notes",
      dataIndex: "notes",
      width: "22%",
      render: (v: string) => v || "-",
    },
    {
      title: "",
      key: "action",
      width: "10%",
      render: (_: unknown, row: StudyBookmark) => (
        <Popconfirm
          title="Remove bookmark?"
          okText="Remove"
          cancelText="Cancel"
          onConfirm={() => handleDelete(row.id)}
        >
          <Button size="small" danger icon={<DeleteOutlined />}>
            Remove
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }} role="main">
      <div className="bookmarks-header">
        <div>
          <h2 style={{ margin: 0 }}>Study Bookmarks</h2>
          <span className="bookmarks-subtitle">
            Bookmark studies for teaching, research, or follow-up
          </span>
        </div>
        <Space>
          <Select
            allowClear
            placeholder="All collections"
            style={{ width: 190 }}
            value={collectionFilter}
            onChange={(v) => setCollectionFilter(v)}
            options={collections.map((c) => ({
              value: c.id,
              label: c.name,
            }))}
          />
          <Button icon={<BookOutlined />} onClick={() => setCollectionOpen(true)}>
            New Collection
          </Button>
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setBookmarkOpen(true)}>
            Bookmark Study
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchBookmarks}>
            Refresh
          </Button>
        </Space>
      </div>

      <PageState
        error={error}
        onRetry={() => fetchBookmarks()}
        empty={!loading && !error && bookmarks.length === 0}
        emptyMessage="No bookmarked studies yet"
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={bookmarks}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </PageState>

      {/* New Collection Modal */}
      <Modal
        title="New Collection"
        open={collectionOpen}
        onCancel={() => setCollectionOpen(false)}
        footer={null}
        width={460}
      >
        <Form form={collectionForm} layout="vertical" onFinish={handleCreateCollection}>
          <Form.Item
            name="name"
            label="Collection Name"
            rules={[{ required: true, message: "Name is required" }]}
          >
            <Input placeholder="e.g. Teaching Cases" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Create Collection
          </Button>
        </Form>
      </Modal>

      {/* Bookmark Study Modal */}
      <Modal
        title="Bookmark Study"
        open={bookmarkOpen}
        onCancel={() => setBookmarkOpen(false)}
        footer={null}
        width={520}
      >
        <Form form={bookmarkForm} layout="vertical" onFinish={handleCreateBookmark}>
          <Form.Item
            name="study_uid"
            label="Study UID"
            rules={[{ required: true, message: "Study UID is required" }]}
          >
            <Input placeholder="e.g. 1.2.840.113619.2.55.3..." />
          </Form.Item>
          <Form.Item name="study_desc" label="Description">
            <Input placeholder="e.g. Chest CT — rare finding" />
          </Form.Item>
          <Form.Item name="collection_id" label="Collection">
            <Select
              allowClear
              placeholder="Select collection (optional)"
              options={collections.map((c) => ({
                value: c.id,
                label: c.name,
              }))}
            />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Teaching point, follow-up note…" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Bookmark Study
          </Button>
        </Form>
      </Modal>
    </Content>
  );
}

export default withSidebar(StudyBookmarks);
