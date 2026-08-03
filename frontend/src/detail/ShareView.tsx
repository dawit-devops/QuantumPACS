import { useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import { Spin } from "antd";

function ShareView() {
  const navigate = useNavigate();
  const { key } = useParams();

  useEffect(() => {
    if (key) {
      sessionStorage.setItem("tempKey", key);
    }
    navigate("/", { replace: true });
  }, [navigate, key]);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
      }}
    >
      <Spin size="large" tip="Opening shared study..." />
    </div>
  );
}

export default ShareView;
