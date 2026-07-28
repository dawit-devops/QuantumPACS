import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '10s', target: 5 },
    { duration: '20s', target: 10 },
    { duration: '30s', target: 10 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080/api';
const TOKEN = __ENV.TOKEN || '';
const SAMPLE_DICOM = __ENV.SAMPLE_DICOM || '';

export default function () {
  if (!SAMPLE_DICOM) {
    console.warn('No SAMPLE_DICOM file provided. Set SAMPLE_DICOM env var.');
    return;
  }

  const file = open(SAMPLE_DICOM, 'b');
  const body = `--BOUNDARY\r\nContent-Type: application/dicom\r\n\r\n${file}\r\n--BOUNDARY--`;

  const params = {
    headers: {
      'Content-Type': 'multipart/related; type=application/dicom; boundary=BOUNDARY',
      Authorization: `Bearer ${TOKEN}`,
    },
  };

  const res = http.post(`${BASE_URL}/dicomweb/studies`, body, params);
  check(res, { 'STOW-RS status 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  sleep(1);
}
