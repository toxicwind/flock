
from services.mildlyawesome.events import EventBus, event_bus

# Export EventBus for easier imports
__all__ = ["EventBus", "event_bus"]

# Lazy singleton accessible via imports
event_bus = EventBus()
