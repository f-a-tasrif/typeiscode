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
        "Platform": {"isSolid": False},
        "Door": {"isOpen": False},
        "Trap": {"isLethal": True},
    }

    #: Some property tokens render with the SAME glyph but spell the key
    #: differently: the `solid` glyph stands for Platform.isSolid *and*
    #: Wall.solid.  A statement assembled with the other spelling (e.g.
    #: `Wall.isSolid = False`) is normalized here so it lands on the key
    #: the engine actually reads, instead of a dead entry nothing looks up.
    _ALIASES: dict[str, dict[str, str]] = {
        "Wall": {"isSolid": "solid"},
        "Platform": {"solid": "isSolid"},
    }

    #: history log of every successful compile, useful for the UI / debugging
    log: list[str] = []

    @classmethod
    def canonical(cls, class_name: str, prop: str) -> str:
        """Spell `prop` the way the engine reads it for `class_name`."""
        return cls._ALIASES.get(class_name, {}).get(prop, prop)

    @classmethod
    def get(cls, class_name: str, prop: str, default=None):
        return cls._data.get(class_name, {}).get(cls.canonical(class_name, prop), default)

    @classmethod
    def set(cls, class_name: str, prop: str, value) -> bool:
        """Returns True if this call actually changed the value."""
        prop = cls.canonical(class_name, prop)
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
