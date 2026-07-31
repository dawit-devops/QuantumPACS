import { Button, Card, Typography } from 'antd';
import { CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

interface ErrorDisplayProps {
  message?: string;
  detail?: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ message, detail, onRetry }: ErrorDisplayProps) {
  return (
    <Card
      style={{
        margin: '48px auto',
        maxWidth: 480,
        textAlign: 'center',
        borderColor: 'var(--color-error, #ef4444)',
      }}
    >
      <CloseCircleOutlined style={{ fontSize: 48, color: 'var(--color-error, #ef4444)', marginBottom: 16 }} />
      <Paragraph>
        <Text strong style={{ fontSize: 16 }}>
          {message || 'Something went wrong'}
        </Text>
      </Paragraph>
      {detail && (
        <Paragraph type="secondary" style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
          {detail}
        </Paragraph>
      )}
      {onRetry && (
        <Button icon={<ReloadOutlined />} onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}
