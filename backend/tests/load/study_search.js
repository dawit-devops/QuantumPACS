import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '10s', target: 5 },
    { duration: '20s', target: 20 },
    { duration: '10s', target: 50 },
    { duration: '30s', target: 50 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080/api';
const TOKEN = __ENV.TOKEN || '';

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/dicom+json',
      Authorization: `Bearer ${TOKEN}`,
    },
  };

  const patientRes = http.get(`${BASE_URL}/dicomweb/studies?PatientID=*&limit=50`, params);
  check(patientRes, { 'patient search status 200': (r) => r.status === 200 });
  errorRate.add(patientRes.status !== 200);

  const modalityRes = http.get(`${BASE_URL}/dicomweb/studies?Modality=CT&limit=50`, params);
  check(modalityRes, { 'modality search status 200': (r) => r.status === 200 });

  sleep(1);
}
