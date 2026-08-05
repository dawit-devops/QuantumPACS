import { NavigateFunction } from "react-router";

let _navigate: NavigateFunction | null = null;

export const setNavigator = (n: NavigateFunction) => {
  _navigate = n;
};

export const navigate = (to: string) => _navigate?.(to);
