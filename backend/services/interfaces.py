from typing import Any, Optional, Protocol, TypeVar

T = TypeVar('T', covariant=True)


class MetadataService(Protocol):
    async def get_patient(self, patient_id: str) -> Optional[dict[str, Any]]:
        ...

    async def get_study(self, study_id: str) -> Optional[dict[str, Any]]:
        ...

    async def get_series(self, series_id: str) -> Optional[dict[str, Any]]:
        ...

    async def add_file(self, file_data: dict[str, Any]) -> dict[str, Any]:
        ...

    async def get_file(self, file_id: str) -> Optional[dict[str, Any]]:
        ...

    async def search_studies(self, query: dict[str, Any]) -> dict[str, Any]:
        ...


class StorageService(Protocol):
    async def store(self, file_data: dict[str, Any], data: bytes) -> bool:
        ...

    async def fetch(self, file_data: dict[str, Any]) -> Optional[bytes]:
        ...

    async def delete(self, file_data: dict[str, Any]) -> bool:
        ...

    async def exists(self, file_data: dict[str, Any]) -> bool:
        ...


class SearchService(Protocol):
    async def index_file(self, file_data: dict[str, Any]) -> bool:
        ...

    async def search(self, query: dict[str, Any]) -> dict[str, Any]:
        ...

    async def delete_from_index(self, file_id: str) -> bool:
        ...


class AuthService(Protocol):
    async def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        ...

    async def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        ...

    async def authorize(self, user: dict[str, Any], permission: str) -> bool:
        ...

    async def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
        ...


class NotificationService(Protocol):
    async def broadcast(self, channel: str, message: dict[str, Any]) -> bool:
        ...

    async def subscribe(self, channel: str, callback: Any) -> bool:
        ...

    async def unsubscribe(self, channel: str) -> bool:
        ...


class ServiceRegistry:
    def __init__(self):
        self._services: dict[type, object] = {}

    def register(self, interface: type, implementation: object) -> None:
        self._services[interface] = implementation

    def get(self, interface: type[T]) -> T:
        impl = self._services.get(interface)
        if impl is None:
            msg = f'No service registered for {interface.__name__}'
            raise KeyError(msg)
        return impl

    def get_or_none(self, interface: type[T]) -> Optional[T]:
        return self._services.get(interface)

    def reset(self) -> None:
        self._services.clear()