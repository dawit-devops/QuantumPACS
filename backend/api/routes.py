import os
from starlette.routing import Router, Route, Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles

from starlette.responses import FileResponse

from api.patient import PatientHandler
from api.files import (
    Upload, DownloadFiles, DownloadData, DownloadToken, FilesHandler, FileHandler,
    FileChangesHandler, ShareFilesHandler, ShareFilesListHandler, ServeFile, ServeThumbnail
)
from api.logs import LogsHandler, LogEventTypesHandler, LogActorsHandler
from api.notifications import NotificationsHandler, NotificationHandler, NotificationsReadAllHandler, NotificationsUnreadCountHandler
from api.replicas import ReplicasHandlers, ReplicaHandlers
from api.roles import RolesHandler, RoleHandler, PermissionsHandler, RoleUsersHandler
from api.tenants import TenantsHandler, TenantHandler, TenantStatsHandler
from api.telemetry import health_endpoint, metrics_endpoint
from api.users import (
    Login, ChangePassword, RefreshToken, Logout, RevokeToken,
    UsersHandler, UsersDeactivate, UsersNewPassword, UserRoleUpdate,
)
from api.account import ProfileHandler
from api.api_keys import ApiKeysHandler, ApiKeyHandler
from api.oauth import oauth_login, oauth_callback, oidc_discovery, oauth_token_exchange
from api.oauth_providers import OAuthProvidersHandler, OAuthProviderHandler, PublicOAuthProvidersHandler
from api.dicomweb import DicomWebStudies, DicomWebWado, DicomWebWadoUri, DicomWebWadoFrames, DicomWebArchive
from api.dicomweb_admin import DicomWebAdminHandler, DicomWebMetricsHandler, DicomWebRequestsHandler
from api.webhooks import WebhooksHandler, WebhookHandler, WebhookTestHandler
from api.fhir import (
    FhirMetadata,
    FhirPatientRoot, FhirPatientResource,
    FhirImagingStudyRead, FhirImagingStudySearch,
    FhirDocumentReferenceRead, FhirDocumentReferenceSearch,
)
from api.fhir_admin import (
    FhirAdminConfigHandler,
    FhirAdminClientsHandler, FhirAdminClientHandler,
    FhirAdminMetricsHandler, FhirAdminRecentRequestsHandler,
    FhirAdminTestHandler,
)
from api.hl7_admin import (
    Hl7MessagesHandler, Hl7MessageHandler,
    Hl7MetricsHandler, Hl7ConfigHandler, Hl7StatusHandler,
)
from api.routing import RoutingHandler, RoutingRuleHandler
from api.hl7 import Hl7Receiver
from api.worklist import WorklistHandler, WorklistEntryHandler, WorklistStationAeHandler
from api.exams import (
    ExamsHandler, ExamHandler, ExamIdentityHandler, ExamProtocolHandler,
    ExamAcquisitionsHandler, ExamAcquisitionDecisionHandler, ExamDoseHandler,
    ExamSafetyHandler, ExamCompleteHandler, ExamIncidentsHandler,
    ExamOverridesHandler, ProtocolsHandler,
)
from api.reports import (
    ReadingListHandler, ExamReportHandler, ExamReportSignHandler,
    ExamAssignHandler,
    ReportTemplatesHandler, PeerReviewReviewersHandler, PeerReviewsHandler,
    PeerReviewHandler, PeerReviewSubmitHandler,
)
from api.reading_presets import ReadingPresetsHandler, ReadingPresetHandler
from api.qa import (
    QAQueueHandler, QAReviewHandler, QAProtocolsHandler, QAProtocolHandler,
    QAIncidentsHandler, QAIncidentHandler, QACorrectiveActionsHandler,
    QACorrectiveActionHandler, QADashboardHandler, QAReviewersHandler,
)
from api.billing import (
    BillingPricingHandler, BillingInvoicesHandler, BillingInvoiceHandler,
    BillingPaymentsHandler, BillingReceiptHandler, BillingClaimsHandler,
    BillingClaimHandler, BillingRefundsHandler, BillingRefundHandler,
    BillingQuotesHandler, BillingPaymentPlansHandler, BillingReconciliationHandler,
)
from api.equipment import (
    EquipmentHandler, EquipmentItemHandler, MaintenanceSchedulesHandler,
    MaintenanceScheduleItemHandler, QCRecordsHandler, DowntimeEventsHandler,
    DowntimeEventHandler, EquipmentOpenDowntimeHandler, WorkOrdersHandler,
    WorkOrderHandler, VendorContractsHandler, VendorContractHandler,
    PartsInventoryHandler, EquipmentReportsHandler,
)
from api.frontdesk import (
    PatientsSearchHandler, PatientsRegistrationHandler, VisitsHandler,
    VisitHandler, VisitOrdersHandler, AppointmentAvailabilityHandler,
    AppointmentsHandler, AppointmentHandler, ConsentsHandler, InsuranceHandler,
    WaitingQueueHandler,
)
from api.portal import (
    PortalScopeHandler, PortalPatientSearchHandler, PortalPatientHandler,
    PortalReportHandler, PortalOrdersHandler, PortalFollowUpHandler,
    PortalFollowUpStatusHandler,
)
from api.dashboard_metrics import DashboardMetricsHandler, DashboardHealthHandler
from api.metering import MeteringUsageHandler, PlatformUsageHandler
from api.tenant_health import TenantHealthHandler
from api.rbac import guard_endpoint_method
from api.permissions import Permission
from api.ws import WSToken, WebsocketHandler
from config import is_docker


DIR = os.path.dirname(os.path.abspath(__file__))


async def docs_page(request):
    return FileResponse(os.path.join(DIR, '..', 'static', 'docs.html'), media_type='text/html')


async def openapi_spec(request):
    return FileResponse(os.path.join(DIR, '..', 'static', 'openapi.json'), media_type='application/json')


_V2_EXCLUDE_PREFIXES = ('/v2/', '/docs', '/api/v2/')


def v2(route_obj):
    """Mark a Route/WebSocketRoute as needing a /v2-prefixed alias."""
    route_obj._v2_alias = True
    return route_obj


_V1_ROUTES = [
    v2(Route('/health', endpoint=health_endpoint)),
    v2(Route('/metrics', endpoint=metrics_endpoint)),
    Route('/docs', endpoint=docs_page),
    Route('/docs/openapi.json', endpoint=openapi_spec),
    v2(Route('/replicas', endpoint=ReplicasHandlers)),
    v2(Route('/replicas/{id}', endpoint=ReplicaHandlers)),
    v2(Route('/login', endpoint=Login)),
    v2(Route('/auth/refresh', endpoint=RefreshToken)),
    v2(Route('/auth/logout', endpoint=Logout)),
    v2(Route('/auth/revoke', endpoint=RevokeToken)),
    v2(Route('/oauth/login', endpoint=oauth_login)),
    v2(Route('/oauth/callback', endpoint=oauth_callback)),
    v2(Route('/.well-known/openid-configuration', endpoint=oidc_discovery)),
    v2(Route('/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])),
    v2(Route('/change_password', endpoint=ChangePassword)),
    v2(Route('/account/profile', endpoint=ProfileHandler)),
    v2(Route('/users', endpoint=UsersHandler)),
    v2(Route('/users/deactivate', endpoint=UsersDeactivate)),
    v2(Route('/users/new_password', endpoint=UsersNewPassword)),
    v2(Route('/users/role', endpoint=UserRoleUpdate)),
    v2(Route('/patients/search', endpoint=PatientsSearchHandler)),
    v2(Route('/patients', endpoint=PatientsRegistrationHandler, methods=['POST'])),
    v2(Route('/patients/{id}/insurance', endpoint=InsuranceHandler)),
    v2(Route('/patients/{id}', endpoint=PatientHandler)),
    v2(Route('/files/upload', endpoint=Upload)),
    v2(Route('/files/download_token', endpoint=DownloadToken)),
    v2(Route('/files/download.zip', endpoint=DownloadFiles)),
    v2(Route('/files/download.csv', endpoint=DownloadData)),
    v2(Route('/files', endpoint=FilesHandler)),
    v2(Route('/files/{id}', endpoint=guard_endpoint_method(FileHandler, 'post', Permission.FILE_WRITE))),
    v2(Route('/files/{id}/changes', endpoint=guard_endpoint_method(FileChangesHandler, 'get', Permission.FILE_READ))),
    v2(Route('/files/{id}/share', endpoint=ShareFilesHandler)),
    v2(Route('/files/{id}/shares', endpoint=ShareFilesListHandler)),
    v2(Route('/files/{id}/shares/{share_id}', endpoint=ShareFilesListHandler)),
    v2(Route('/files/{id}/data', endpoint=ServeFile)),
    v2(Route('/files/{id}/thumbnail', endpoint=ServeThumbnail)),
    v2(Route('/logs', endpoint=LogsHandler)),
    v2(Route('/logs/event-types', endpoint=LogEventTypesHandler)),
    v2(Route('/logs/actors', endpoint=LogActorsHandler)),
    v2(Route('/roles', endpoint=RolesHandler)),
    v2(Route('/roles/{id}', endpoint=RoleHandler)),
    v2(Route('/roles/{id}/users', endpoint=RoleUsersHandler)),
    v2(Route('/permissions', endpoint=PermissionsHandler)),
    v2(Route('/notifications', endpoint=NotificationsHandler)),
    v2(Route('/notifications/unread-count', endpoint=NotificationsUnreadCountHandler)),
    v2(Route('/notifications/read-all', endpoint=NotificationsReadAllHandler)),
    v2(Route('/notifications/{id}', endpoint=NotificationHandler)),
    v2(Route('/tenants', endpoint=TenantsHandler)),
    v2(Route('/tenants/health', endpoint=TenantHealthHandler)),
    v2(Route('/tenants/{id}', endpoint=TenantHandler)),
    v2(Route('/tenants/{id}/stats', endpoint=TenantStatsHandler)),
    v2(Route('/tenants/{id}/usage', endpoint=MeteringUsageHandler)),
    v2(Route('/usage', endpoint=PlatformUsageHandler)),
    v2(Route('/api-keys', endpoint=ApiKeysHandler)),
    v2(Route('/api-keys/{id}', endpoint=ApiKeyHandler)),
    v2(Route('/oauth/providers', endpoint=OAuthProvidersHandler)),
    v2(Route('/oauth/providers/public', endpoint=PublicOAuthProvidersHandler)),
    v2(Route('/oauth/providers/{id}', endpoint=OAuthProviderHandler)),
    v2(Route('/dicomweb/studies', endpoint=DicomWebStudies)),
    v2(Route('/dicomweb/studies/{study_uid}', endpoint=DicomWebWado)),
    v2(Route('/dicomweb/studies/{study_uid}/series', endpoint=DicomWebStudies)),
    v2(Route('/dicomweb/studies/{study_uid}/series/{series_uid}', endpoint=DicomWebWado)),
    v2(Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances', endpoint=DicomWebStudies)),
    v2(Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}', endpoint=DicomWebWado)),
    v2(Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frame_number}', endpoint=DicomWebWadoFrames)),
    # Study-scoped STOW-RS (PS3.18 §10.5): store one or more instances into
    # a study. POST /dicomweb/studies stores without a pre-specified study.
    v2(Route('/dicomweb/studies/{study_uid}/instances', endpoint=DicomWebStudies, methods=['POST'])),
    # Streamed study/series ZIP export (HI-08).
    v2(Route('/dicomweb/studies/{study_uid}/archive', endpoint=DicomWebArchive)),
    v2(Route('/dicomweb/studies/{study_uid}/series/{series_uid}/archive', endpoint=DicomWebArchive)),
    v2(Route('/wado', endpoint=DicomWebWadoUri)),
    v2(Route('/dicomweb/admin', endpoint=DicomWebAdminHandler)),
    v2(Route('/dicomweb/admin/metrics', endpoint=DicomWebMetricsHandler)),
    v2(Route('/dicomweb/admin/requests', endpoint=DicomWebRequestsHandler)),
    v2(Route('/webhooks/test', endpoint=WebhookTestHandler, methods=['POST'])),
    v2(Route('/webhooks', endpoint=WebhooksHandler)),
    v2(Route('/webhooks/{id}', endpoint=WebhookHandler)),
    v2(Route('/fhir/metadata', endpoint=FhirMetadata)),
    v2(Route('/fhir/Patient', endpoint=FhirPatientRoot)),
    v2(Route('/fhir/Patient/{id}', endpoint=FhirPatientResource)),
    v2(Route('/fhir/ImagingStudy', endpoint=FhirImagingStudySearch)),
    v2(Route('/fhir/ImagingStudy/{id}', endpoint=FhirImagingStudyRead)),
    v2(Route('/fhir/DocumentReference', endpoint=FhirDocumentReferenceSearch)),
    v2(Route('/fhir/DocumentReference/{id}', endpoint=FhirDocumentReferenceRead)),
    v2(Route('/hl7', endpoint=Hl7Receiver, methods=['POST'])),
    v2(Route('/hl7/admin/messages', endpoint=Hl7MessagesHandler)),
    v2(Route('/hl7/admin/messages/{id}', endpoint=Hl7MessageHandler)),
    v2(Route('/hl7/admin/metrics', endpoint=Hl7MetricsHandler)),
    v2(Route('/hl7/admin/config', endpoint=Hl7ConfigHandler)),
    v2(Route('/hl7/admin/status', endpoint=Hl7StatusHandler)),
    v2(Route('/worklist/station-aes', endpoint=WorklistStationAeHandler)),
    v2(Route('/worklist', endpoint=WorklistHandler)),
    v2(Route('/worklist/{id}', endpoint=WorklistEntryHandler)),
    v2(Route('/exams', endpoint=ExamsHandler)),
    v2(Route('/exams/{id}', endpoint=ExamHandler)),
    v2(Route('/exams/{id}/identity-confirm', endpoint=ExamIdentityHandler)),
    v2(Route('/exams/{id}/protocol', endpoint=ExamProtocolHandler)),
    v2(Route('/exams/{id}/acquisitions', endpoint=ExamAcquisitionsHandler)),
    v2(Route('/exams/{id}/acquisitions/{aid}/{decision}', endpoint=ExamAcquisitionDecisionHandler)),
    v2(Route('/exams/{id}/dose', endpoint=ExamDoseHandler)),
    v2(Route('/exams/{id}/safety-checks', endpoint=ExamSafetyHandler)),
    v2(Route('/exams/{id}/complete', endpoint=ExamCompleteHandler)),
    v2(Route('/exams/{id}/incidents', endpoint=ExamIncidentsHandler)),
    v2(Route('/exams/{id}/overrides', endpoint=ExamOverridesHandler)),
    v2(Route('/protocols', endpoint=ProtocolsHandler)),
    v2(Route('/reports/reading-list', endpoint=ReadingListHandler)),
    v2(Route('/reports/reading-list/{exam_id}/assign', endpoint=ExamAssignHandler)),
    v2(Route('/reports/templates', endpoint=ReportTemplatesHandler)),
    v2(Route('/reports/{exam_id}', endpoint=ExamReportHandler)),
    v2(Route('/reports/{exam_id}/sign', endpoint=ExamReportSignHandler)),
    v2(Route('/peer-reviews/reviewers', endpoint=PeerReviewReviewersHandler)),
    v2(Route('/peer-reviews', endpoint=PeerReviewsHandler)),
    v2(Route('/peer-reviews/{id}', endpoint=PeerReviewHandler)),
    v2(Route('/peer-reviews/{id}/submit', endpoint=PeerReviewSubmitHandler)),
    v2(Route('/reading-presets', endpoint=ReadingPresetsHandler)),
    v2(Route('/reading-presets/{id}', endpoint=ReadingPresetHandler)),
    v2(Route('/qa/queue', endpoint=QAQueueHandler)),
    v2(Route('/qa/reviews/{exam_id}', endpoint=QAReviewHandler)),
    v2(Route('/qa/reviews', endpoint=QAReviewHandler, methods=['POST'])),
    v2(Route('/qa/protocols', endpoint=QAProtocolsHandler)),
    v2(Route('/qa/protocols/{id}', endpoint=QAProtocolHandler)),
    v2(Route('/qa/incidents', endpoint=QAIncidentsHandler)),
    v2(Route('/qa/incidents/{id}/resolve', endpoint=QAIncidentHandler)),
    v2(Route('/qa/corrective-actions', endpoint=QACorrectiveActionsHandler)),
    v2(Route('/qa/corrective-actions/{id}/resolve', endpoint=QACorrectiveActionHandler)),
    v2(Route('/qa/dashboard', endpoint=QADashboardHandler)),
    v2(Route('/qa/reviewers', endpoint=QAReviewersHandler)),
    v2(Route('/routing', endpoint=RoutingHandler)),
    v2(Route('/routing/{id}', endpoint=RoutingRuleHandler)),
    v2(Route('/fhir/admin/config', endpoint=FhirAdminConfigHandler)),
    v2(Route('/fhir/admin/clients', endpoint=FhirAdminClientsHandler)),
    v2(Route('/fhir/admin/clients/{id}', endpoint=FhirAdminClientHandler)),
    v2(Route('/fhir/admin/metrics', endpoint=FhirAdminMetricsHandler)),
    v2(Route('/fhir/admin/requests', endpoint=FhirAdminRecentRequestsHandler)),
    v2(Route('/fhir/admin/test', endpoint=FhirAdminTestHandler)),
    Route('/v2/dashboard/metrics', endpoint=DashboardMetricsHandler),
    Route('/v2/dashboard/health', endpoint=DashboardHealthHandler),
    v2(Route('/visits', endpoint=VisitsHandler)),
    v2(Route('/visits/{id}', endpoint=VisitHandler)),
    v2(Route('/visits/{id}/orders', endpoint=VisitOrdersHandler)),
    v2(Route('/visits/{id}/consents', endpoint=ConsentsHandler)),
    v2(Route('/visits/{id}/consents/attach', endpoint=ConsentsHandler)),
    v2(Route('/schedule/availability', endpoint=AppointmentAvailabilityHandler)),
    v2(Route('/appointments', endpoint=AppointmentsHandler)),
    v2(Route('/appointments/{id}', endpoint=AppointmentHandler)),
    v2(Route('/insurance/{id}', endpoint=InsuranceHandler)),
    v2(Route('/queue', endpoint=WaitingQueueHandler)),
    v2(Route('/equipment/pm', endpoint=MaintenanceSchedulesHandler)),
    v2(Route('/equipment/downtime/open', endpoint=EquipmentOpenDowntimeHandler)),
    v2(Route('/equipment/reports/compliance', endpoint=EquipmentReportsHandler)),
    v2(Route('/equipment/reports/uptime', endpoint=EquipmentReportsHandler)),
    v2(Route('/equipment/reports/downtime-causes', endpoint=EquipmentReportsHandler)),
    v2(Route('/equipment', endpoint=EquipmentHandler)),
    v2(Route('/equipment/{id}', endpoint=EquipmentItemHandler)),
    v2(Route('/equipment/schedules/{id}', endpoint=MaintenanceScheduleItemHandler)),
    v2(Route('/equipment/{id}/qc', endpoint=QCRecordsHandler)),
    v2(Route('/equipment/{id}/schedules', endpoint=MaintenanceSchedulesHandler)),
    v2(Route('/equipment/{id}/downtime', endpoint=DowntimeEventsHandler)),
    v2(Route('/equipment/{id}/downtime/{downtime_id}', endpoint=DowntimeEventHandler)),
    v2(Route('/equipment/{id}/contracts', endpoint=VendorContractsHandler)),
    v2(Route('/vendor-contracts/{id}', endpoint=VendorContractHandler)),
    v2(Route('/work-orders', endpoint=WorkOrdersHandler)),
    v2(Route('/work-orders/{id}', endpoint=WorkOrderHandler)),
    v2(Route('/parts', endpoint=PartsInventoryHandler)),
    v2(Route('/parts/{id}', endpoint=PartsInventoryHandler, methods=['PUT'])),
    v2(Route('/billing/pricing', endpoint=BillingPricingHandler)),
    v2(Route('/billing/invoices', endpoint=BillingInvoicesHandler)),
    v2(Route('/billing/invoices/{id}', endpoint=BillingInvoiceHandler)),
    v2(Route('/billing/invoices/{id}/payments', endpoint=BillingPaymentsHandler)),
    v2(Route('/billing/payments/{payment_id}/receipt', endpoint=BillingReceiptHandler)),
    v2(Route('/billing/invoices/{id}/claims', endpoint=BillingClaimsHandler)),
    v2(Route('/billing/claims/{id}', endpoint=BillingClaimHandler)),
    v2(Route('/billing/refunds', endpoint=BillingRefundsHandler)),
    v2(Route('/billing/invoices/{id}/refunds', endpoint=BillingRefundsHandler)),
    v2(Route('/billing/refunds/{id}', endpoint=BillingRefundHandler)),
    v2(Route('/billing/quotes', endpoint=BillingQuotesHandler)),
    v2(Route('/billing/invoices/{id}/plans', endpoint=BillingPaymentPlansHandler)),
    v2(Route('/billing/reconciliation', endpoint=BillingReconciliationHandler)),
    v2(Route('/billing/reconciliation/close', endpoint=BillingReconciliationHandler)),
    v2(Route('/portal/scope', endpoint=PortalScopeHandler)),
    v2(Route('/portal/scope/{id}', endpoint=PortalScopeHandler, methods=['DELETE'])),
    v2(Route('/portal/patients', endpoint=PortalPatientSearchHandler)),
    v2(Route('/portal/patients/{patient_id}', endpoint=PortalPatientHandler)),
    v2(Route('/portal/patients/{patient_id}/reports/{report_id}', endpoint=PortalReportHandler)),
    v2(Route('/portal/patients/{patient_id}/orders', endpoint=PortalOrdersHandler)),
    v2(Route('/portal/follow-ups', endpoint=PortalFollowUpHandler)),
    v2(Route('/portal/follow-ups/{id}', endpoint=PortalFollowUpStatusHandler, methods=['PUT'])),
    v2(Route('/ws_token', endpoint=WSToken)),
    v2(WebSocketRoute('/ws', endpoint=WebsocketHandler)),
]


def _alias_path(path: str) -> str:
    if path.startswith('/v2/'):
        return path
    return '/v2' + path


def _build_v2_aliases(v1_routes):
    aliases = []
    for r in v1_routes:
        if not isinstance(r, (Route, WebSocketRoute)):
            continue
        if not getattr(r, '_v2_alias', False):
            continue
        if any(r.path.startswith(p) for p in _V2_EXCLUDE_PREFIXES):
            continue
        aliases.append(type(r)(_alias_path(r.path), endpoint=r.endpoint))
    return aliases


_V2_ALIASES = _build_v2_aliases(_V1_ROUTES)

routes = _V1_ROUTES + _V2_ALIASES
routes = [
    Mount('/api', app=Router(routes)),
]
if is_docker():
    routes.append(Mount('/', app=StaticFiles(directory='static'), name="static"))
