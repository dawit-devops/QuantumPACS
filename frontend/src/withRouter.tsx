import React from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';

export default function withRouter(Component: React.ComponentType<any>) {
  return function Wrapped(props: any) {
    const navigate = useNavigate();
    const params = useParams();
    const location = useLocation();

    const match = { params };

    return (
      <Component
        {...props}
        history={{
          ...location,
          location,
          push: navigate,
          replace: (to: string) => navigate(to, { replace: true }),
        }}
        match={match}
        location={location}
        navigate={navigate}
      />
    );
  };
}
