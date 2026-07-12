"""Django integration for PGSync.

Define search indexes declaratively from Django models and let PGSync
handle change data capture from PostgreSQL to Elasticsearch/OpenSearch.
"""

__version__ = "0.1.0"

from .indexes import Nested, PGSyncIndex, registry  # noqa: F401
