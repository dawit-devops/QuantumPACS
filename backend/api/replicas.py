from starlette.endpoints import HTTPEndpoint

from api.response import ok, created
from api.utils import is_admin
from api.validate import parse_body
from api.schemas.replicas import CreateReplicaRequest, UpdateReplicaRequest
from db.conn import get_conn
from db.replica import Replica
from db.replica_files import ReplicaFiles


class ReplicasHandlers(HTTPEndpoint):
    async def post(self, request):
        is_admin(request)
        body = await parse_body(CreateReplicaRequest, request)

        async with get_conn()as conn:
            async with conn.transaction():
                replica = Replica(conn)
                result = await replica.add(body.type, body.model_dump(exclude_none=True))

                master = await replica.master()
                if not master:
                    master_id = result
                    await replica.set_master(result)
                else:
                    master_id = master['id']

                await ReplicaFiles(conn).add_replica(result, master_id)

        return created({'id': result})

    async def get(self, request):
        is_admin(request)
        async with get_conn() as conn:
            replicas = await Replica(conn).get_all()

        return ok({'data': replicas})


class ReplicaHandlers(HTTPEndpoint):
    async def post(self, request):
        is_admin(request)
        body = await parse_body(UpdateReplicaRequest, request)
        replica_id = int(request.path_params['id'])

        async with get_conn() as conn:
            if body.master:
                await Replica(conn).set_master(replica_id)
            if body.delay is not None:
                await Replica(conn).update_delay(replica_id, body.delay)

        return ok({})

    async def delete(self, request):
        is_admin(request)
        replica_id = int(request.path_params['id'])

        async with get_conn() as conn:
            await Replica(conn).delete(replica_id)

        return ok({})
