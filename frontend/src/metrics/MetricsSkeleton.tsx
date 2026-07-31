import { Skeleton, Card, Row, Col } from "antd";

export function MetricsSkeleton() {
  return (
    <div data-testid="metrics-skeleton" style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Col key={i} xs={12} sm={8} lg={4}>
            <Card>
              <Skeleton.Input active size="small" block />
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} md={8}>
          <Card>
            <Skeleton active paragraph={{ rows: 5 }} title />
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card>
            <Skeleton active paragraph={{ rows: 6 }} title />
          </Card>
          <Card style={{ marginTop: 16 }}>
            <Skeleton active paragraph={{ rows: 4 }} title />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card>
            <Skeleton active paragraph={{ rows: 6 }} title />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <Skeleton active paragraph={{ rows: 4 }} title />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
