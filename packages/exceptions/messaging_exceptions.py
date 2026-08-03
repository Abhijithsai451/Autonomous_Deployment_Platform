# packages/messaging/exceptions.py

class MessagingError(Exception):
    """Base exception for all messaging package errors."""
    pass


class MessageDeserializationError(MessagingError):
    """Raised when an incoming NATS message cannot be deserialized or validated."""
    pass


class EventRegistrationError(MessagingError):
    """Raised when an event type fails registration or lookup in EventRegistry."""
    pass