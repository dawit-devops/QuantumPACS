import { Empty, Typography } from "antd";

import type { ReactNode } from "react";

const { Paragraph } = Typography;

interface EmptyStateProps {
  description?: string;
  action?: ReactNode;
  title?: string;
}

export function EmptyState({ description, action, title }: EmptyStateProps) {
  return (
    <div style={{ margin: "64px auto", textAlign: "center" }}>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            {title && (
              <Paragraph strong style={{ marginBottom: 4, fontSize: 15 }}>
                {title}
              </Paragraph>
            )}
            <Paragraph type="secondary" style={{ margin: 0 }}>
              {description || "No data"}
            </Paragraph>
          </div>
        }
      >
        {action}
      </Empty>
    </div>
  );
}

export function renderEmpty(_componentName?: string) {
  return <EmptyState />;
}
