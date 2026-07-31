import os.path
import tempfile
from tempfile import SpooledTemporaryFile

import aiobotocore.session
from starlette.responses import RedirectResponse

from storage.storage import Storage


class S3Storage(Storage):
    name = 's3'

    def __init__(self, replica):
        self.access_key_id = replica['meta']['access_key_id']
        self.secret_access_key = replica['meta']['secret_access_key']
        self.session = aiobotocore.session.get_session()
        self.bucket = 'quantumpacs'
        self.region = replica['location']
        self._client = None

    @staticmethod
    def default_config():
        return {
            'location': 'eu-central-1',
        }

    async def _get_client(self):
        if self._client is None:
            self._client = await self.session.create_client(
                's3',
                region_name=self.region,
                aws_secret_access_key=self.secret_access_key,
                aws_access_key_id=self.access_key_id,
            ).__aenter__()
        return self._client

    async def init(self):
        client = await self._get_client()
        try:
            await client.create_bucket(
                Bucket=self.bucket,
                CreateBucketConfiguration={
                    'LocationConstraint': self.region,
                },
            )
        except Exception as e:
            if 'BucketAlreadyOwnedByYou' not in str(e):
                raise

    async def index(self):
        client = await self._get_client()
        paginator = client.get_paginator('list_objects')
        async for result in paginator.paginate(Bucket=self.bucket):
            for c in result.get('Contents', []):
                try:
                    patient_id, study_id, series_id, name = c['Key'].split('/')
                    if study_id == 'empty':
                        study_id = ''
                    if series_id == 'empty':
                        series_id = ''
                except Exception:
                    continue

                yield {
                    'patient_id': patient_id,
                    'study_id': study_id,
                    'series_number': series_id,
                    'name': name,
                    'location': c['Key'],
                    'hash': c['ETag'].replace('"', ''),
                }

    def get_key(self, filedata):
        return os.path.join(
            str(filedata['patient_id']),
            str(filedata['study_id']) or 'empty',
            str(filedata['series_number']) or 'empty',
            filedata['name'],
        )

    async def copy(self, src, filedata):
        key = self.get_key(filedata)

        if isinstance(src, str):
            with open(src, 'rb') as f:
                client = await self._get_client()
                await client.put_object(
                    Bucket=self.bucket, Key=key, Body=f,
                )
        else:
            body = src
            if isinstance(src, SpooledTemporaryFile):
                src.seek(0)
            client = await self._get_client()
            await client.put_object(
                Bucket=self.bucket, Key=key, Body=body,
            )
        return {
            'location': key
        }

    async def fetch(self, filedata):
        key = self.get_key(filedata)
        client = await self._get_client()
        response = await client.get_object(Bucket=self.bucket, Key=key)
        tmp = tempfile.NamedTemporaryFile(delete=False)
        async with response['Body'] as stream:
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                tmp.write(chunk)
        tmp.flush()
        tmp.seek(0)
        return tmp

    async def serve(self, filedata):
        client = await self._get_client()
        url = await client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': filedata['location']},
            ExpiresIn=3600,
        )
        return RedirectResponse(url=url)

    async def delete(self, filedata):
        key = self.get_key(filedata)
        client = await self._get_client()
        await client.delete_object(Bucket=self.bucket, Key=key)
