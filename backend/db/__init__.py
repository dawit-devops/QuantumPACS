import importlib
import typing


_module_registry = [
    'db.files',
    'db.file_changes',
    'db.log',
    'db.patient',
    'db.study',
    'db.series',
    'db.replica',
    'db.replica_files',
    'db.share_files',
    'db.users',
    'db.tenants',
    'db.oauth_providers',
    'db.hl7_message',
    'db.routing_rule',
    'db.exams',
    'db.reports',
]

_registered = False


def register_tables():
    global _registered
    if _registered:
        return
    from db.table import Table
    _classes = [
        ('db.log', 'Log'),
        ('db.patient', 'Patient'),
        ('db.replica', 'Replica'),
        ('db.study', 'Study'),
        ('db.series', 'Series'),
        ('db.files', 'Files'),
        ('db.users', 'Users'),
        ('db.file_changes', 'FileChange'),
        ('db.replica_files', 'ReplicaFiles'),
        ('db.share_files', 'SharedFiles'),
        ('db.tenants', 'Tenants'),
        ('db.oauth_providers', 'OAuthProviders'),
        ('db.hl7_message', 'Hl7Message'),
        ('db.hl7_message', 'Hl7ParseError'),
        ('db.routing_rule', 'RoutingRule'),
        ('db.exams', 'Exams'),
        ('db.exams', 'Acquisitions'),
        ('db.exams', 'SafetyChecks'),
        ('db.exams', 'Incidents'),
        ('db.exams', 'ProtocolOverrides'),
        ('db.exams', 'Protocols'),
        ('db.reports', 'Reports'),
        ('db.reports', 'ReportTemplates'),
        ('db.reports', 'PeerReviews'),
    ]
    for mod_path, cls_name in _classes:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        Table.register(cls)
    _registered = True


def __getattr__(name: str) -> typing.Any:
    for mod_path in _module_registry:
        mod = importlib.import_module(mod_path)
        if hasattr(mod, name):
            attr = getattr(mod, name)
            return attr
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
