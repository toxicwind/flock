from .client import FlockClient
from .models import Models
from .nim import Flock, create_flock_client, Nim
from .keypool import FlockKeyPool, parse_retry_after_ms, split_keys

# Deprecated aliases kept for one release cycle after the nim -> flock rename.
NimClient = FlockClient
create_nim_client = create_flock_client

__all__ = ["FlockClient", "Models", "Flock", "create_flock_client", "Nim",
           "FlockKeyPool", "parse_retry_after_ms", "split_keys",
           "NimClient", "create_nim_client"]
__version__ = "1.0.0"
