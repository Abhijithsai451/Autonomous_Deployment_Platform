from typing import Type, Dict, Any


class EventRegistry:
    """Registers the mapping event name to concrete BaseEvent Classes"""
    _registry: Dict[str, Type[Any]] = {}

    @classmethod
    def register(cls, event_cls: Type[Any])-> None:
        cls._registry[event_cls.__name__] = event_cls

    @classmethod
    def get(cls, event_name: str)->Type[Any]:
        if event_name not in cls._registry:
            raise KeyError(f"Event Type '{event_name}' not registered in the Event Registry. ")
        return cls._registry.get(event_name)



