import React from "react";
import { useLocation, useNavigate } from "react-router";
import { parseParams, encodeQuery } from "../helpers";

function LinkExt(props: any) {
  let { reload } = props;
  const location = useLocation();
  const navigate = useNavigate();
  let { pathname, search } = location;
  let loc = pathname + search;
  let href: string | undefined;

  if (props.to) {
    href = props.to;
  } else if (props.query) {
    if (loc.includes("?")) {
      let params = parseParams(search);
      params = Object.assign(params, props.query);
      href = pathname + "?" + encodeQuery(params);
    } else {
      href = loc + "?" + encodeQuery(props.query);
    }
  }

  const onNavigate = (event: React.MouseEvent) => {
    event.preventDefault();

    if (loc !== href && href) {
      navigate(href);
    } else {
      if (reload) reload();
    }
  };

  return (
    <a href={href} onClick={onNavigate}>
      {props.children}
    </a>
  );
}

export default LinkExt;
