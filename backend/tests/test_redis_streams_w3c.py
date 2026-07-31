from unittest.mock import AsyncMock, MagicMock, patch



class TestW3CTracePropagation:
    async def test_publish_includes_traceparent_in_message(self):
        from services.redis_streams import StreamProducer

        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value='1-0')

        producer = StreamProducer(mock_redis)

        with patch('opentelemetry.propagate.inject') as mock_inject:
            def fake_inject(carrier):
                carrier['traceparent'] = '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01'

            mock_inject.side_effect = fake_inject

            await producer.publish('test-stream', {'data': 'x'})

            mock_inject.assert_called_once()
            call_args = mock_redis.xadd.call_args.args
            msg_data = call_args[1]
            traceparent = msg_data.get(b'traceparent') or msg_data.get('traceparent')
            assert traceparent is not None
            assert traceparent.startswith(b'00-') or traceparent.startswith('00-')

    async def test_publish_without_active_span_succeeds(self):
        from services.redis_streams import StreamProducer

        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value='1-0')

        producer = StreamProducer(mock_redis)
        with patch('opentelemetry.propagate.inject'):
            msg_id = await producer.publish('test-stream', {'data': 'x'})
            assert msg_id == '1-0'

    async def test_consume_extracts_trace_context(self):
        from services.redis_streams import StreamConsumer

        mock_redis = AsyncMock()
        mock_redis.xreadgroup = AsyncMock(return_value=[
            (b'test-stream', [
                (b'1-0', {
                    b'event_type': b'x',
                    b'data': b'{}',
                    b'traceparent': b'00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01',
                }),
            ]),
        ])

        consumer = StreamConsumer(mock_redis)

        extracted = MagicMock()
        with patch('opentelemetry.propagate.extract', return_value=extracted) as mock_extract:
            with patch('opentelemetry.context.attach') as mock_attach:
                mock_attach.return_value = 'token'
                await consumer.poll('test-stream', 'g', 'c', count=10, block=100)
                mock_extract.assert_called_once()
                mock_attach.assert_any_call(extracted)

    async def test_consume_treats_block_timeout_as_empty_poll(self):
        from redis.exceptions import TimeoutError as RedisTimeoutError

        from services.redis_streams import StreamConsumer

        mock_redis = AsyncMock()
        mock_redis.xreadgroup = AsyncMock(side_effect=RedisTimeoutError(
            'Timeout reading from localhost:6380',
        ))

        consumer = StreamConsumer(mock_redis)
        result = await consumer.poll('test-stream', 'g', 'c', count=10, block=5000)

        assert result == []
        mock_redis.xreadgroup.assert_awaited_once_with(
            'g', 'c', {'test-stream': '>'}, count=10, block=5000,
        )

    async def test_consume_still_raises_other_errors(self):
        from services.redis_streams import StreamConsumer

        mock_redis = AsyncMock()
        mock_redis.xreadgroup = AsyncMock(
            side_effect=ConnectionError('refused'),
        )

        consumer = StreamConsumer(mock_redis)
        try:
            await consumer.poll('test-stream', 'g', 'c', count=10, block=5000)
            assert False, 'expected ConnectionError to propagate'
        except ConnectionError:
            pass
