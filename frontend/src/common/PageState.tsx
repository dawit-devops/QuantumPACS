import type { ReactNode } from "react";
import { Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { EmptyState } from "./EmptyState";
import { ErrorDisplay } from "./ErrorDisplay";

interface PageStateProps {
  loading?: boolean;
  error?: string | null;
  errorDetail?: string;
  empty?: boolean;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  onRetry?: () => void;
  children?: ReactNode;
}

const spinIcon = <LoadingOutlined style={{ fontSize: 32 }} spin />;

function stateKey({
  loading,
  error,
  empty,
}: {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
}): string {
  if (loading) return "loading";
  if (error) return "error";
  if (empty) return "empty";
  return "content";
}

export function PageState({
  loading,
  error,
  errorDetail,
  empty,
  emptyMessage,
  emptyAction,
  onRetry,
  children,
}: PageStateProps) {
  const sk = stateKey({ loading, error, empty });
  const content = (() => {
    if (loading) {
      return (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            minHeight: 240,
          }}
        >
          <Spin indicator={spinIcon} />
        </div>
      );
    }

    if (error) {
      return (
        <ErrorDisplay message={error} detail={errorDetail} onRetry={onRetry} />
      );
    }

    if (empty) {
      return <EmptyState description={emptyMessage} action={emptyAction} />;
    }

    return <>{children}</>;
  })();

  return (
    <div key={sk} className="state-enter">
      {content}
    </div>
  );
}
