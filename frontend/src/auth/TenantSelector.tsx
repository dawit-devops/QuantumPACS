import React, { useState, useEffect } from "react";
import { Select, Typography, Spin } from "antd";
import { useAuth } from "./AuthContext";
import { request } from "../helpers";

const { Text } = Typography;

export default function TenantSelector() {
  const { isAuthenticated, activeTenant, setActiveTenant } = useAuth();
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    setLoading(true);
    request("v2/tenants")
      .then((res: any) => setTenants(res?.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated || !activeTenant) return null;

  const handleChange = (slug: string) => {
    const t = tenants.find((t: any) => t.slug === slug);
    if (t) {
      setActiveTenant({ id: t.id, name: t.name, slug: t.slug });
      localStorage.setItem("tenant_id", t.slug);
      localStorage.setItem("tenant_name", t.name);
    }
  };

  const options = tenants.map((t: any) => ({
    value: t.slug,
    label: t.name,
  }));

  return (
    <div
      style={{
        padding: "8px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <Text
        type="secondary"
        style={{
          fontSize: 11,
          display: "block",
          marginBottom: 4,
          color: "rgba(255,255,255,0.45)",
        }}
      >
        Tenant
      </Text>
      {loading ? (
        <Spin size="small" />
      ) : options.length > 1 ? (
        <Select
          value={activeTenant.slug}
          onChange={handleChange}
          options={options}
          size="small"
          style={{ width: "100%" }}
          popupMatchSelectWidth={false}
        />
      ) : (
        <Text style={{ color: "#fff", fontSize: 13 }}>{activeTenant.name}</Text>
      )}
    </div>
  );
}
