"""Complete VIEW DEFINITION catalog; administrative CONTROL is not required."""

from app.channels_catalog import metadata as previous_metadata
from app.parity_channels.policy import VERSION
from tools.foundation_snapshot import records


def metadata(cursor):
    result = previous_metadata(cursor)
    result["version"] = VERSION
    result["object_owners"] = records(
        cursor,
        """SELECT s.name AS schema_name,
      o.name AS object_name,o.type,USER_NAME(o.principal_id) AS explicit_owner,
      USER_NAME(COALESCE(o.principal_id,s.principal_id)) AS effective_owner
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,o.type""",
    )
    return result
