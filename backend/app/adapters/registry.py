from .base import BaseAdapter
from .boss import BossAdapter
from .job51 import Job51Adapter
from .liepin import LiepinAdapter
from .zhilian import ZhilianAdapter


_ADAPTERS: dict[str, BaseAdapter] = {
    "boss": BossAdapter(),
    "liepin": LiepinAdapter(),
    "zhilian": ZhilianAdapter(),
    "job51": Job51Adapter(),
}


def get_adapter(platform: str) -> BaseAdapter:
    return _ADAPTERS[platform]


def list_adapters() -> list[BaseAdapter]:
    return list(_ADAPTERS.values())

