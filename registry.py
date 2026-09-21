"""
registry.py
-----------
PropertyRegistry is the single "master dictionary" the whole game reads
from. It maps ClassName -> {propertyName: value}. When a circuit line on
the grid successfully compiles a statement like `Platform.isSolid = true`,
the engine calls PropertyRegistry.set("Platform", "isSolid", True) and
every Platform instance in the level will see the new value on the very
next tick (see GameObject.is_blocking implementations), because they
always look the value up live rather than caching it.
"""


class PropertyRegistry:
    _data: dict[str, dict[str, object]] = {
        "Wall": {"solid": True},
        "Platform": {"isSolid": True},
        "Door": {"isOpen": False},
        "Trap": {"isLethal": True},
    }

    #: history log of every successful compile, useful for the UI / debugging
    log: list[str] = []

    @classmethod
    def get(cls, class_name: str, prop: str, default=None):
        return cls._data.get(class_name, {}).get(prop, default)

    @classmethod
    def set(cls, class_name: str, prop: str, value) -> bool:
        """Returns True if this call actually changed the value."""
        bucket = cls._data.setdefault(class_name, {})
        changed = bucket.get(prop) != value
        bucket[prop] = value
        cls.log.append(f"{class_name}.{prop} = {value}")
        return changed

    @classmethod
    def snapshot(cls) -> dict:
        return {k: dict(v) for k, v in cls._data.items()}

    @classmethod
    def reset(cls, initial: dict) -> None:
        cls._data = {k: dict(v) for k, v in initial.items()}
        cls.log = []
