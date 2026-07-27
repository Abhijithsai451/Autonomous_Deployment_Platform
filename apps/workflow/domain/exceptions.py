class WorkflowDomainError(Exception):
    """Base exception class for workflow domain errors"""
    pass

class InvalidStateTransitionError(WorkflowDomainError):
    """
    Raises an Exception when an invalid state transition is attempted on an instance or task.
    """
    def __init__(self, entity_name:str, entity_id: str, current_state: str, action: str):
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.current_state = current_state
        self.action = action

        super().__init__(
            f"Cannot execute action '{action}' on {entity_name} {entity_id} "
            f"while in state '{current_state}'."
        )