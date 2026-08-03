from enum import Enum


class Permission(str, Enum):
    FILE_READ = 'FILE_READ'
    FILE_WRITE = 'FILE_WRITE'
    FILE_DELETE = 'FILE_DELETE'
    PATIENT_READ = 'PATIENT_READ'
    PATIENT_WRITE = 'PATIENT_WRITE'
    STUDY_READ = 'STUDY_READ'
    STUDY_WRITE = 'STUDY_WRITE'
    USER_READ = 'USER_READ'
    USER_WRITE = 'USER_WRITE'
    USER_DELETE = 'USER_DELETE'
    USER_ADMIN = 'USER_ADMIN'
    REPLICA_READ = 'REPLICA_READ'
    REPLICA_WRITE = 'REPLICA_WRITE'
    REPLICA_DELETE = 'REPLICA_DELETE'
    LOG_READ = 'LOG_READ'
    TENANT_READ = 'TENANT_READ'
    TENANT_WRITE = 'TENANT_WRITE'
    TENANT_ADMIN = 'TENANT_ADMIN'
    ROLE_READ = 'ROLE_READ'
    ROLE_WRITE = 'ROLE_WRITE'
    ROLE_DELETE = 'ROLE_DELETE'
    SERVICE_KEY_READ = 'SERVICE_KEY_READ'
    SERVICE_KEY_WRITE = 'SERVICE_KEY_WRITE'
    SERVICE_KEY_DELETE = 'SERVICE_KEY_DELETE'
    WORKLIST_READ = 'WORKLIST_READ'
    WORKLIST_WRITE = 'WORKLIST_WRITE'
    EXAM_READ = 'EXAM_READ'
    EXAM_WRITE = 'EXAM_WRITE'
    REPORT_READ = 'REPORT_READ'
    REPORT_WRITE = 'REPORT_WRITE'
    REPORT_SIGN = 'REPORT_SIGN'
    PEER_REVIEW_READ = 'PEER_REVIEW_READ'
    PEER_REVIEW_WRITE = 'PEER_REVIEW_WRITE'
    QA_READ = 'QA_READ'
    QA_WRITE = 'QA_WRITE'
    PROTOCOL_MANAGE = 'PROTOCOL_MANAGE'
    DICOMWEB_READ = 'DICOMWEB_READ'
    DICOMWEB_WRITE = 'DICOMWEB_WRITE'
    ROUTING_READ = 'ROUTING_READ'
    ROUTING_WRITE = 'ROUTING_WRITE'
    METRICS_READ = 'METRICS_READ'
    SYSTEM_ADMIN = 'SYSTEM_ADMIN'
    HL7_READ = 'HL7_READ'
    HL7_WRITE = 'HL7_WRITE'


PERMISSION_GROUPS = {
    'Files': ['FILE_READ', 'FILE_WRITE', 'FILE_DELETE'],
    'Patients': ['PATIENT_READ', 'PATIENT_WRITE'],
    'Studies': ['STUDY_READ', 'STUDY_WRITE'],
    'Users': ['USER_READ', 'USER_WRITE', 'USER_DELETE', 'USER_ADMIN'],
    'Replicas': ['REPLICA_READ', 'REPLICA_WRITE', 'REPLICA_DELETE'],
    'Logs': ['LOG_READ'],
    'Tenants': ['TENANT_READ', 'TENANT_WRITE', 'TENANT_ADMIN'],
    'Roles': ['ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE'],
    'Service Keys': ['SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE'],
    'Worklist': ['WORKLIST_READ', 'WORKLIST_WRITE'],
    'Exams': ['EXAM_READ', 'EXAM_WRITE'],
    'Reports': ['REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN'],
    'Peer Review': ['PEER_REVIEW_READ', 'PEER_REVIEW_WRITE'],
    'QA': ['QA_READ', 'QA_WRITE', 'PROTOCOL_MANAGE'],
    'DICOMweb': ['DICOMWEB_READ', 'DICOMWEB_WRITE'],
    'Routing': ['ROUTING_READ', 'ROUTING_WRITE'],
    'Metrics': ['METRICS_READ'],
    'HL7': ['HL7_READ', 'HL7_WRITE'],
    'System Admin': ['SYSTEM_ADMIN'],
}

SUPER_ADMIN_PERMISSIONS = {p.value for p in Permission}


BUILT_IN_ROLES = {
    'super_admin': list(SUPER_ADMIN_PERMISSIONS),
    'admin': [
        Permission.FILE_READ.value, Permission.FILE_WRITE.value, Permission.FILE_DELETE.value,
        Permission.PATIENT_READ.value, Permission.PATIENT_WRITE.value,
        Permission.STUDY_READ.value, Permission.STUDY_WRITE.value,
        Permission.USER_READ.value, Permission.USER_WRITE.value,
        Permission.REPLICA_READ.value, Permission.REPLICA_WRITE.value,
        Permission.LOG_READ.value,
        Permission.ROLE_READ.value, Permission.ROLE_WRITE.value,
        Permission.SERVICE_KEY_READ.value, Permission.SERVICE_KEY_WRITE.value,
        Permission.SERVICE_KEY_DELETE.value,
        Permission.WORKLIST_READ.value, Permission.WORKLIST_WRITE.value,
        Permission.EXAM_READ.value, Permission.EXAM_WRITE.value,
        Permission.REPORT_READ.value, Permission.REPORT_WRITE.value, Permission.REPORT_SIGN.value,
        Permission.PEER_REVIEW_READ.value, Permission.PEER_REVIEW_WRITE.value,
        Permission.DICOMWEB_READ.value, Permission.DICOMWEB_WRITE.value,
        Permission.ROUTING_READ.value, Permission.ROUTING_WRITE.value,
        Permission.METRICS_READ.value,
        Permission.SYSTEM_ADMIN.value,
        Permission.HL7_READ.value, Permission.HL7_WRITE.value,
    ],
    'technologist': [
        Permission.FILE_READ.value, Permission.FILE_WRITE.value, Permission.FILE_DELETE.value,
        Permission.PATIENT_READ.value, Permission.PATIENT_WRITE.value,
        Permission.STUDY_READ.value, Permission.STUDY_WRITE.value,
        Permission.WORKLIST_READ.value, Permission.WORKLIST_WRITE.value,
        Permission.EXAM_READ.value, Permission.EXAM_WRITE.value,
        Permission.DICOMWEB_READ.value,
    ],
    'radiologist': [
        Permission.FILE_READ.value,
        Permission.PATIENT_READ.value,
        Permission.STUDY_READ.value,
        Permission.EXAM_READ.value,
        Permission.REPORT_READ.value,
        Permission.REPORT_WRITE.value,
        Permission.REPORT_SIGN.value,
        Permission.PEER_REVIEW_READ.value,
        Permission.PEER_REVIEW_WRITE.value,
        Permission.DICOMWEB_READ.value,
    ],
    'qa_team': [
        Permission.FILE_READ.value,
        Permission.PATIENT_READ.value,
        Permission.STUDY_READ.value,
        Permission.EXAM_READ.value,
        Permission.QA_READ.value,
        Permission.QA_WRITE.value,
        Permission.PROTOCOL_MANAGE.value,
        Permission.PEER_REVIEW_READ.value,
        Permission.PEER_REVIEW_WRITE.value,
        Permission.DICOMWEB_READ.value,
        Permission.METRICS_READ.value,
    ],
    'physician': [
        Permission.FILE_READ.value,
        Permission.PATIENT_READ.value,
        Permission.STUDY_READ.value,
        Permission.DICOMWEB_READ.value,
    ],
    'tenant_admin': [
        Permission.FILE_READ.value, Permission.FILE_WRITE.value, Permission.FILE_DELETE.value,
        Permission.PATIENT_READ.value, Permission.PATIENT_WRITE.value,
        Permission.STUDY_READ.value, Permission.STUDY_WRITE.value,
        Permission.USER_READ.value, Permission.USER_WRITE.value,
        Permission.REPLICA_READ.value, Permission.REPLICA_WRITE.value,
        Permission.LOG_READ.value,
        Permission.ROLE_READ.value, Permission.ROLE_WRITE.value,
        Permission.WORKLIST_READ.value, Permission.WORKLIST_WRITE.value,
        Permission.METRICS_READ.value,
    ],
    'cashier': [
        Permission.PATIENT_READ.value,
        Permission.PATIENT_WRITE.value,
    ],
}