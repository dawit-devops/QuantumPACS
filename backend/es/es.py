import os

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch import ConnectionError as ESConnectionError

from config import config
from es.mapping import INDEX

client = {}
INDEX_NAME = 'quantumpacs'


async def setup():
    host = config['es_host']
    if not host.startswith('http'):
        host = f'http://{host}:9200'
    conn = AsyncElasticsearch(
        hosts=[host],
        connections_per_node=4,
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
    client[os.getpid()] = conn
    try:
        await get_client().info()
    except (ESConnectionError, OSError, Exception):
        from log import get_logger
        get_logger(__name__).warning('Elasticsearch not available — search disabled')
        client[os.getpid()] = None
        return
    try:
        await get_client().indices.get(index=INDEX_NAME)
    except NotFoundError:
        try:
            await get_client().indices.create(
                index=INDEX_NAME,
                settings=INDEX['settings'],
                mappings=INDEX['mappings'],
            )
        except Exception:
            from log import get_logger
            get_logger(__name__).warning('Failed to create ES index — search disabled')
            client[os.getpid()] = None


async def teardown():
    if get_client():
        await close()
    if os.getpid() in client:
        del client[os.getpid()]


async def close():
    c = get_client()
    if c:
        await c.close()


def get_client():
    return client.get(os.getpid())


async def index(data):
    c = get_client()
    if c:
        await c.index(index=INDEX_NAME, id=str(data['id']), document=data)


async def delete(id_):
    c = get_client()
    if c:
        try:
            await c.delete(index=INDEX_NAME, id=str(id_))
        except NotFoundError:
            pass


columns = [
    "Patient's Name", 'SOP Class UID', 'Study Description', 'Series Description',
    "Referring Physician's Name", "Performing Physician's Name",
]


async def search(data):
    c = get_client()
    if not c:
        return {'data': [], 'total': 0}
    size = data.get('results', 10)
    page = data.get('page', 1)

    query = data.get('query', '').lower()
    if query != '':
        es_q = {
            "multi_match": {
                "query": query,
                "fields": [
                    "Patient ID",
                    "Patient's Name.lang_analyzed",
                    "SOP Class UID.lang_analyzed",
                    "Study Description.lang_analyzed",
                    "Series Modality",
                    "Series Description.lang_analyzed",
                    "Referring Physician's Name.lang_analyzed",
                    "Performing Physician's Name.lang_analyzed",
                ],
                "operator": "and",
            }
        }
    elif len(data) > 0:
        es_q = []

        for k, v in data.items():
            if not v: continue

            if k in columns:
                k += ".lang_analyzed"
            es_q.append({"match": {k: v[0] if isinstance(v, list) and len(v) > 0 else v}})

        es_q = {"bool": {"must": es_q}}
    else:
        es_q = {"match_all": {}}

    res = await get_client().search(
        index=INDEX_NAME,
        query=es_q,
        size=size,
        from_=(page - 1) * size,
    )
    total = res['hits']['total']
    if isinstance(total, dict):
        total = total['value']
    return {
        'data': [r['_source'] for r in res['hits']['hits']],
        'total': total,
    }


async def index_file(file):
    data = {
        'id': file['id'],
        'patient_db_id': file['patient_db_id'],
        'study_db_id': file['study_db_id'],
        'series_db_id': file['series_db_id'],
    }
    data.update(file['meta'])
    await index(data)


async def reset_index():
    c = get_client()
    if not c:
        return
    await c.indices.delete(index='quantumpacs')
    await c.indices.create(
        index='quantumpacs',
        settings=INDEX['settings'],
        mappings=INDEX['mappings'],
    )
