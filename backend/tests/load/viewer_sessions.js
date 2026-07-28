import { check, sleep, group } from 'k6';
import ws from 'k6/ws';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '10s', target: 10 },
    { duration: '20s', target: 50 },
    { duration: '30s', target: 50 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    ws_session_duration: ['p(95)<60000'],
    errors: ['rate<0.10'],
  },
};

const WS_URL = __ENV.WS_URL || 'ws://localhost:8080/api/ws';
const TOKEN = __ENV.TOKEN || '';

export default function () {
  const url = `${WS_URL}?token=${TOKEN}`;

  ws.connect(url, { tags: { type: 'viewer' } }, function (socket) {
    socket.on('open', function () {
      socket.send(JSON.stringify({ type: 'ping' }));
    });

    socket.on('message', function (data) {
      const msg = JSON.parse(data);
      if (msg.type === 'pong') {
        check(msg, { 'pong received': (m) => m.type === 'pong' });
      }
    });

    socket.on('error', function (e) {
      errorRate.add(1);
      console.error('WS error:', e);
    });

    socket.setTimeout(function () {
      socket.close();
    }, 10000);

    sleep(5);
  });
}
