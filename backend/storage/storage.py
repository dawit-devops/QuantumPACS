import asyncio


class Storage:
    storage_types = {}
    storages = {}
    _init_locks = {}

    @staticmethod
    def register(cls):
        Storage.storage_types[cls.name] = cls

    @staticmethod
    def get_class(type_):
        return Storage.storage_types[type_]

    @staticmethod
    def default_config_by_type(type_):
        return Storage.get_class(type_).default_config()

    @staticmethod
    def default_config():
        return {}

    @staticmethod
    async def get(replica):
        rid = replica['id']

        if rid not in Storage.storages:
            if rid not in Storage._init_locks:
                Storage._init_locks[rid] = asyncio.Lock()
            async with Storage._init_locks[rid]:
                if rid not in Storage.storages:
                    cls = Storage.get_class(replica['type'])
                    s = cls(replica)
                    await s.init()
                    Storage.storages[rid] = s

        return Storage.storages[rid]

    async def init(self):
        pass

    async def index(self):
        raise NotImplementedError

    async def copy(self, src, file_data):
        raise NotImplementedError

    async def fetch(self, file_data):
        raise NotImplementedError

    async def serve(self, file_data):
        raise NotImplementedError

    async def delete(self, file_data):
        raise NotImplementedError
