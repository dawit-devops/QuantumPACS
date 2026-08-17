import { Button, Card, Typography } from "antd";
import {
  CloseCircleOutlined,
  HomeOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { landingRouteFor } from "../navigator";

const { Text, Paragraph } = Typography;

interface ErrorDisplayProps {
  message?: string;
  detail?: string;
  onRetry?: () => void;
}

// Care-coordinator review (P2-2): a "Missing permission" failure is not
// transient — Retry can never succeed. Detect it, drop the Retry button, and
// offer the user's own landing route instead of a dead retry loop. The
// permission name is kept in the detail line so the user knows what to ask an
// administrator for.
export function ErrorDisplay({ message, detail, onRetry }: ErrorDisplayProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isPermissionError = /missing permission/i.test(message ?? "");

  return (
    <Card
      style={{
        margin: "48px auto",
        maxWidth: 480,
        textAlign: "center",
        borderColor: "var(--color-error, #ef4444)",
      }}
    >
      <CloseCircleOutlined
        style={{
          fontSize: 48,
          color: "var(--color-error, #ef4444)",
          marginBottom: 16,
        }}
      />
      <Paragraph>
        <Text strong style={{ fontSize: 16 }}>
          {isPermissionError
            ? "You don't have access to this area"
            : message || "Something went wrong"}
        </Text>
      </Paragraph>
      {(detail || isPermissionError) && (
        <Paragraph
          type="secondary"
          style={{ fontSize: 13, whiteSpace: "pre-wrap" }}
          role={isPermissionError ? "alert" : undefined}
        >
          {isPermissionError
            ? `${message}. Ask an administrator to grant this access for your role.`
            : detail}
        </Paragraph>
      )}
      {onRetry && !isPermissionError && (
        <Button icon={<ReloadOutlined />} onClick={onRetry}>
          Retry
        </Button>
      )}
      {isPermissionError && user && (
        <Button
          icon={<HomeOutlined />}
          onClick={() => navigate(landingRouteFor(user))}
        >
          Go to home
        </Button>
      )}
    </Card>
  );
}
