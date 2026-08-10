declare module "react-highlight-words";
declare module "dicom-parser";

declare module "*.css";
declare module "*.svg";
declare module "*.png";
declare module "*.jpg";

// (R1-05) import.meta.env (DEV etc.) is used by Login.tsx to gate the
// demo-user datalist to development builds.
interface ImportMeta {
  env: {
    DEV: boolean;
    PROD: boolean;
    MODE: string;
    [key: string]: any;
  };
}

interface Window {
  cornerstone: any;
  cornerstoneTools: any;
  cornerstoneWADOImageLoader: any;
  ctinit: any;
}
