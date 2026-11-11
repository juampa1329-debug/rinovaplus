"""SQL Server NVARCHAR limits count UTF-16 code units, not Python characters."""


def sql_text(value, units):
    return (
        str(value)
        .encode("utf-16-le", errors="replace")[: units * 2]
        .decode("utf-16-le", errors="ignore")
    )
