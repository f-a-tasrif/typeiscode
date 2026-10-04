

class PropertyRegistry:
    _data: dict[str, dict[str, object]] = {
        "Wall": {"solid": True},
        "Platform": {"isSolid": False},
        "Door": {"isOpen": False},
        "Trap": {"isLethal": True},
        "Stone": {"solid": True},
        "Seal": {"active": True},
        "Flag": {"moved": False},
    }






    _ALIASES: dict[str, dict[str, str]] = {
        "Wall": {"isSolid": "solid"},
        "Platform": {"solid": "isSolid"},
        "Stone": {"isSolid": "solid"},
    }


    log: list[str] = []

    @classmethod
    def canonical(cls, class_name: str, prop: str) -> str:
        return cls._ALIASES.get(class_name, {}).get(prop, prop)

    @classmethod
    def get(cls, class_name: str, prop: str, default=None):
        return cls._data.get(class_name, {}).get(cls.canonical(class_name, prop), default)

    @classmethod
    def set(cls, class_name: str, prop: str, value) -> bool:
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
