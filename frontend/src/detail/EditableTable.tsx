import React, { useState, useRef, useEffect, useContext } from "react";
import { Table, Input, Form, message } from "antd";
import type { FormInstance, InputRef } from "antd";
import { request } from "../helpers";

const EditableContext = React.createContext<FormInstance<any> | null>(null);

const EditableRow = ({ index, ...props }: any) => {
  const [form] = Form.useForm();
  return (
    <EditableContext.Provider value={form}>
      <tr {...props} />
    </EditableContext.Provider>
  );
};

const editableFields: string[] = [];

const EditableCell = (props: any) => {
  let [editing, setEditing] = useState(false);
  let form = useContext(EditableContext);
  let input = useRef<InputRef>(null);

  const toggleEdit = () => {
    if (!editableFields.includes(props.record.key)) return;
    setEditing(!editing);
  };

  useEffect(() => {
    if (editing) {
      input.current?.focus();
    }
  }, [editing]);

  const save = async () => {
    const { record, handleSave } = props;
    try {
      const values = await form!.validateFields();
      toggleEdit();
      if (record.value !== values.value) {
        handleSave({ ...record, ...values });
      }
    } catch (err) {
      // validation failed
    }
  };

  const { children, dataIndex, record, title } = props;
  return editing ? (
    <Form.Item style={{ margin: 0 }}>
      {React.cloneElement(
        <Input ref={input} onPressEnter={save} onBlur={save} />,
        {
          onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
            form!.setFieldsValue({ [dataIndex]: e.target.value }),
        },
      )}
    </Form.Item>
  ) : (
    <div
      className="editable-cell-value-wrap"
      style={{ paddingRight: 24 }}
      onClick={toggleEdit}
    >
      {children}
    </div>
  );
};

const EditableTable = (props: any) => {
  let columns = [
    {
      title: "key",
      dataIndex: "key",
      width: "20%",
    },
    {
      title: "value",
      dataIndex: "value",
      editable: true,
      width: "70%",
    },
  ];
  let [dataSource, setDataSource] = useState(props.file.meta);
  let [search, setSearch] = useState("");

  const metaToDatasource = () => {
    let ds = Object.entries(props.file.meta || {}).map((e) => {
      return { key: e[0], value: e[1] };
    });
    return ds.sort((a: any, b: any) => a.key.localeCompare(b.key));
  };

  useEffect(() => {
    const ds = metaToDatasource();
    setDataSource(ds);
    setSearch("");
    // eslint-disable-next-line
  }, [props.file]);

  useEffect(() => {
    let ds = metaToDatasource();
    ds = ds.filter((d: any) =>
      d.key.toLowerCase().startsWith(search.toLowerCase()),
    );
    setDataSource(ds);
    // eslint-disable-next-line
  }, [search]);

  const onSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
  };

  const handleSave = (row: any) => {
    const newData = [...dataSource];
    const index = newData.findIndex((item: any) => row.key === item.key);
    const item = newData[index];
    request(`files/${props.file.id}`, { data: { tag: row } })
      .then(() => {
        newData.splice(index, 1, {
          ...item,
          ...row,
        });
        setDataSource(newData);
      })
      .catch(() => message.error("Failed to save"));
  };

  const components = {
    body: {
      row: EditableRow,
      cell: EditableCell,
    },
  };
  const cols = columns.map((col) => {
    if (!(col as any).editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record: any) => ({
        record,
        editable: (col as any).editable,
        dataIndex: col.dataIndex,
        title: col.title,
        handleSave: handleSave,
      }),
    };
  });
  return (
    <div style={props.style}>
      <Input
        placeholder="Search..."
        onChange={onSearchChange}
        value={search}
      ></Input>
      <Table
        scroll={{ x: 500 }}
        components={components}
        rowClassName={() => "editable-row"}
        bordered
        dataSource={dataSource}
        columns={cols}
        loading={props.loading}
        pagination={props.pagination}
        rowKey={props.rowKey}
      />
    </div>
  );
};

export default EditableTable;
