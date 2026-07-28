import type { ReactNode } from 'react';
import { Empty } from 'antd';

interface EmptyStateProps {
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ description, action }: EmptyStateProps) {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={description || 'No data'}
    >
      {action}
    </Empty>
  );
}

export function renderEmpty(_componentName?: string) {
  return <EmptyState />;
}
