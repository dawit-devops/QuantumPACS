from db.table import Table
from db.files import Files
from db.file_changes import FileChange
from db.log import Log
from db.patient import Patient
from db.study import Study
from db.series import Series
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.share_files import SharedFiles
from db.users import Users
from db.tenants import Tenants
from db.oauth_providers import OAuthProviders
from db.hl7_message import Hl7Message, Hl7ParseError
from db.routing_rule import RoutingRule


Table.register(Log)
Table.register(Patient)
Table.register(Replica)
Table.register(Study)
Table.register(Series)
Table.register(Files)
Table.register(Users)
Table.register(FileChange)
Table.register(ReplicaFiles)
Table.register(SharedFiles)
Table.register(Tenants)
Table.register(OAuthProviders)
Table.register(Hl7Message)
Table.register(Hl7ParseError)
Table.register(RoutingRule)
