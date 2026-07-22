declare module 'react-highlight-words';
declare module 'cornerstone-core';
declare module 'cornerstone-math';
declare module 'cornerstone-tools';
declare module 'cornerstone-wado-image-loader';
declare module 'cornerstone-web-image-loader';
declare module 'hammerjs';
declare module 'dicom-parser';

declare module '*.css';
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';

interface Window {
  cornerstone: any;
  cornerstoneTools: any;
  cornerstoneWADOImageLoader: any;
  ctinit: any;
}
