"""RIS Study Bookmarks API (R-08).

Radiologists bookmark studies for teaching, research, and follow-up into
named collections. Endpoints for listing/creating collections and
bookmarks, plus deleting individual bookmarks. User-scoped — endpoints
read the authenticated user's id from the request context.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_bookmarks import (
    CreateCollectionRequest, CreateBookmarkRequest,
)
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class BookmarkCollectionsHandler(HTTPEndpoint):
    """R-08: GET /ris/bookmark-collections (list) and POST (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_bookmarks import BookmarkCollections
            rows = await BookmarkCollections(conn).list(
                tenant, user_id=str(request.user.id))
        return ok({'data': rows})

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateCollectionRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_bookmarks import BookmarkCollections
            row = await BookmarkCollections(conn).create(
                user_id=str(request.user.id),
                name=body.name,
                description=body.description,
                by=str(request.user.id),
                tenant_id=tenant,
            )
        return created({'data': row})


class StudyBookmarksHandler(HTTPEndpoint):
    """R-08: GET /ris/bookmarks (list) and POST /ris/bookmarks (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        collection_id = request.query_params.get('collection_id')
        async with get_conn() as conn:
            from db.ris_bookmarks import StudyBookmarks
            rows = await StudyBookmarks(conn).list(
                tenant, user_id=str(request.user.id),
                collection_id=collection_id)
        return ok({'data': rows})

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateBookmarkRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_bookmarks import StudyBookmarks
            row = await StudyBookmarks(conn).create(
                user_id=str(request.user.id),
                study_uid=body.study_uid,
                study_desc=body.study_desc,
                collection_id=body.collection_id,
                notes=body.notes,
                tenant_id=tenant,
            )
        return created({'data': row})


class StudyBookmarkDeleteHandler(HTTPEndpoint):
    """R-08: DELETE /ris/bookmarks/{id} — remove a bookmark."""

    @requires_permission(Permission.PATIENT_WRITE)
    async def delete(self, request):
        bookmark_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_bookmarks import StudyBookmarks
            existing = await StudyBookmarks(conn).get(bookmark_id, tenant)
            if not existing:
                return not_found('Bookmark not found')
            await StudyBookmarks(conn).delete(
                bookmark_id, tenant_id=tenant)
        return ok({'status': 'deleted'})