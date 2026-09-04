import React, { useState } from "react";
import { Button, Card, Divider, Typography, Select } from "antd";
import { BankOutlined, CreditCardOutlined, PayCircleOutlined } from "@ant-design/icons";
import { submitPayment } from "../api/checkin";

const { Title, Text } = Typography;

interface CoPayPromptProps {
  token: string;
  amount: number;
  onComplete: (receipt: { receipt_number: string }) => void;
  onSkip: () => void;
}

// K-04: co-pay collection prompt after kiosk check-in. Cash / card / check
// via the token-scoped payment endpoint; "Pay later" keeps the balance
// outstanding for the billing queue (spec §2.13 K-04).
function CoPayPrompt({ token, amount, onComplete, onSkip }: CoPayPromptProps) {
  const [method, setMethod] = useState<"cash" | "card" | "check">("cash");
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState("");

  const handlePay = async () => {
    setPaying(true);
    setError("");
    try {
      const res = await submitPayment(token, {
        method,
        amount,
        idempotency_key: `kiosk-${token.slice(0, 16)}-${Date.now()}`,
      });
      onComplete(res.receipt);
    } catch (e: any) {
      setError(e?.message || "Payment failed — please see the front desk.");
    } finally {
      setPaying(false);
    }
  };

  return (
    <div className="kiosk-center" data-testid="checkin-copay">
      <div className="kiosk-card kiosk-copay">
        <Title level={4} className="kiosk-title">
          <PayCircleOutlined style={{ marginRight: 8 }} />
          Co-pay Due
        </Title>
        <Text type="secondary">
          A co-pay of ${amount.toFixed(2)} is due for this visit.
        </Text>
        <div className="kiosk-copay-amount">${amount.toFixed(2)}</div>

        {error && (
          <Text type="danger" style={{ display: "block", marginBottom: 8 }}>
            {error}
          </Text>
        )}

        <Divider style={{ margin: "12px 0" }} />

        <Select
          value={method}
          onChange={setMethod}
          style={{ width: "100%", marginBottom: 12 }}
          data-testid="copay-method"
          options={[
            { value: "cash", label: "Cash" },
            { value: "card", label: "Credit / Debit Card" },
            { value: "check", label: "Check" },
          ]}
        />

        <div className="kiosk-copay-methods">
          <Button
            className="kiosk-copay-method"
            type="primary"
            size="large"
            icon={<BankOutlined />}
            loading={paying}
            onClick={handlePay}
            data-testid="copay-pay"
          >
            Pay Now
          </Button>
        </div>

        <Button
          type="link"
          onClick={onSkip}
          className="kiosk-copay-skip"
          data-testid="copay-skip"
        >
          Pay later — I'll take care of it at the front desk
        </Button>
      </div>
    </div>
  );
}

export default CoPayPrompt;