import pytest
from pydantic import BaseModel
from starlette.requests import Request

from api.validate import parse_body, _ValidationException, validation_exception_handler


class SampleSchema(BaseModel):
    name: str
    age: int


class EmptySchema(BaseModel):
    pass


def _make_request(body):
    async def _json():
        return body
    req = Request({'type': 'http', 'method': 'POST'})
    req.json = _json
    return req


class TestParseBody:
    @pytest.mark.asyncio
    async def test_valid_body_parses_correctly(self):
        req = _make_request({'name': 'Alice', 'age': 30})
        result = await parse_body(SampleSchema, req)
        assert isinstance(result, SampleSchema)
        assert result.name == 'Alice'
        assert result.age == 30

    @pytest.mark.asyncio
    async def test_missing_required_field_raises(self):
        req = _make_request({'name': 'Bob'})
        with pytest.raises(_ValidationException) as exc:
            await parse_body(SampleSchema, req)
        assert any(d['field'] == 'age' for d in exc.value.details)

    @pytest.mark.asyncio
    async def test_wrong_type_raises(self):
        req = _make_request({'name': 'Alice', 'age': 'not-a-number'})
        with pytest.raises(_ValidationException) as exc:
            await parse_body(SampleSchema, req)
        assert any(d['field'] == 'age' for d in exc.value.details)

    @pytest.mark.asyncio
    async def test_extra_fields_ignored_by_default(self):
        req = _make_request({'name': 'Alice', 'age': 30, 'extra': 'field'})
        result = await parse_body(SampleSchema, req)
        assert result.name == 'Alice'
        assert result.age == 30
        assert not hasattr(result, 'extra')

    @pytest.mark.asyncio
    async def test_empty_body_missing_all_fields(self):
        req = _make_request({})
        with pytest.raises(_ValidationException) as exc:
            await parse_body(SampleSchema, req)
        fields = {d['field'] for d in exc.value.details}
        assert 'name' in fields
        assert 'age' in fields

    @pytest.mark.asyncio
    async def test_empty_schema_accepts_empty_body(self):
        req = _make_request({})
        result = await parse_body(EmptySchema, req)
        assert isinstance(result, EmptySchema)

    @pytest.mark.asyncio
    async def test_none_value_raises(self):
        req = _make_request({'name': None, 'age': 30})
        with pytest.raises(_ValidationException) as exc:
            await parse_body(SampleSchema, req)
        assert any(d['field'] == 'name' for d in exc.value.details)

    @pytest.mark.asyncio
    async def test_null_body_raises_type_error(self):
        req = _make_request(None)
        with pytest.raises(TypeError):
            await parse_body(SampleSchema, req)

    @pytest.mark.asyncio
    async def test_invalid_json_body_raises(self):
        async def _broken_json():
            raise ValueError('Invalid JSON')
        req = _make_request(None)
        req.json = _broken_json
        with pytest.raises(ValueError):
            await parse_body(SampleSchema, req)

    def test_exception_handler_returns_api_error_response(self):
        exc = _ValidationException([{'field': 'name', 'message': 'Field required', 'type': 'missing'}])
        resp = validation_exception_handler(None, exc)
        assert resp.status_code == 422
        import json
        body = json.loads(resp.body)
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert body['error']['details'][0]['field'] == 'name'
