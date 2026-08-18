from storage.storage import Storage
from storage.local_storage import LocalStorage
from storage.s3 import S3Storage
from storage.b2 import B2Storage

Storage.register(LocalStorage)
Storage.register(S3Storage)
Storage.register(B2Storage)

# The e2e/CI seed (ci.yml "Seed master replica") inserts the master replica
# with type='fs' (filesystem); without this alias, backups and DICOM
# STOW/WADO 500 with KeyError('fs').
Storage.storage_types['fs'] = LocalStorage