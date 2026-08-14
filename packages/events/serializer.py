import json
from typing import Union, Dict, Any, Tuple

from pydantic import ValidationError

from packages.events.base import BaseEvent
from packages.events.event_envelope import EventEnvelope
from packages.events.event_registry import EventRegistry
from packages.exceptions.messaging_exceptions import MessageDeserializationError


class EventSerializer:
    """
    Handles serialization and deserialization of NATS event Envelope and typed Events
    """
    @staticmethod
    def deserialize_envelope(data: Union[str, bytes, Dict[str, Any]]) -> EventEnvelope:
        try:
            if isinstance(data, (bytes, str)):
                payload_dict = json.loads(data)
            else:
                payload_dict = data

            return EventEnvelope.model_validate(payload_dict)
        except (json.JSONDecodeError, ValidationError) as err:
            raise MessageDeserializationError(f"Failed to parse EventEnvelope from payload: {err}") from err

    @classmethod
    def deserialize_event(cls, data: Union[str, bytes, Dict[str, Any]]) -> Tuple[BaseEvent, EventEnvelope]:
        """
        Unpacks an EventEnvelope and uses EventRegistry to deserialize
        the inner payload back into its concrete BaseEvent subclass.
        """
        envelope = cls.deserialize_envelope(data)

        try:
            event_cls = EventRegistry.get(envelope.event_type)
        except KeyError as err:
            raise MessageDeserializationError(
                f"Unknown event type '{envelope.event_type}'. Ensure the event class is imported."
            ) from err

        try:
            # 2. Instantiate concrete event using the envelope payload
            typed_event = event_cls.model_validate(envelope.payload)
            return typed_event, envelope
        except ValidationError as err:
            raise MessageDeserializationError(
                f"Failed to validate typed event '{envelope.event_type}': {err}"
            ) from err