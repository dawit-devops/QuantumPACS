import React, { useState, useEffect } from "react";
import { Select, Typography, Spin } from "antd";
import { useAuth } from "./AuthContext";
import { listSessionTenants } from "../api/tenants";
import { emit } from "../helpers";

const { Text } = Typography;

export default function TenantSelector() {
  const { isAuthenticated, activeTenant, setActiveTenant } = useAuth();
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    setLoading(true);
    listSessionTenants()
      .then(setTenants)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  // No dead "Tenant" caption without a tenant: the sidebar block only
  // exists once the user actually has an active tenant to show.
  if (!isAuthenticated || !activeTenant) return null;

  const handleChange = (slug: string) => {
    const t = tenants.find((t: any) => t.slug === slug);
    if (t) {
      setActiveTenant({ id: t.id, name: t.name, slug: t.slug });
      localStorage.setItem("tenant_id", t.slug);
      localStorage.setItem("tenant_name", t.name);
      // Screens subscribed via useTenantRefetch() refetch on this event.
      emit("tenant:changed", t.slug);
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
      {loading ? (
        <Spin size="small" />
      ) : options.length > 1 ? (
        <>
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
          <Select
            value={activeTenant.slug}
            onChange={handleChange}
            options={options}
            size="small"
            style={{ width: "100%" }}
            popupMatchSelectWidth={false}
          />
        </>
      ) : (
        // Single-tenant (or tenant fetch failed): show the name, no caption.
        <Text style={{ color: "#fff", fontSize: 13 }}>{activeTenant.name}</Text>
      )}
    </div>
  );
}
