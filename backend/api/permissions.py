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
    DICOMWEB_READ = 'DICOMWEB_READ'
    DICOMWEB_WRITE = 'DICOMWEB_WRITE'
    ROUTING_READ = 'ROUTING_READ'
    ROUTING_WRITE = 'ROUTING_WRITE'


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
        Permission.DICOMWEB_READ.value, Permission.DICOMWEB_WRITE.value,
        Permission.ROUTING_READ.value, Permission.ROUTING_WRITE.value,
    ],
    'technologist': [
        Permission.FILE_READ.value, Permission.FILE_WRITE.value, Permission.FILE_DELETE.value,
        Permission.PATIENT_READ.value, Permission.PATIENT_WRITE.value,
        Permission.STUDY_READ.value, Permission.STUDY_WRITE.value,
        Permission.WORKLIST_READ.value, Permission.WORKLIST_WRITE.value,
        Permission.DICOMWEB_READ.value,
    ],
    'radiologist': [
        Permission.FILE_READ.value,
        Permission.PATIENT_READ.value,
        Permission.STUDY_READ.value,
        Permission.DICOMWEB_READ.value,
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
    ],
    'cashier': [
        Permission.PATIENT_READ.value,
        Permission.PATIENT_WRITE.value,
    ],
}