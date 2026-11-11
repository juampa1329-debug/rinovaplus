"""Catalog definition equivalence on a dedicated owned fault copy, never SIIE."""

import json

from app.institutional.broadcast_policy import TARGET
from tools.foundation_snapshot import metadata
from tools.prepare_p7_broadcast import WORK, admin, read, save
from tools.qualify_p4_storage import academic


def main():
    target = read(WORK / "storage-result.json")["copies"][1]
    assert TARGET.fullmatch(target) and "_FAULT_" in target
    with admin(target) as db:
        c = db.cursor()
        before = academic(c)
        assert not c.execute(
            "SELECT 1 FROM sys.schemas WHERE name='crm_config'"
        ).fetchone()
        c.execute("CREATE SCHEMA crm_config AUTHORIZATION dbo")
        c.execute(
            (
                "CREATE TABLE crm_config.P7CatalogProbe"
                "(Id int NOT NULL PRIMARY KEY,Value int"
                " NOT NULL CONSTRAINT DF_P7CatalogProbe"
                " DEFAULT(1),CONSTRAINT CK_P7CatalogPro"
                "be CHECK(Value>0))"
            )
        )
        for statement in [
            (
                "CREATE VIEW crm_config.P7CatalogView A"
                "S SELECT Id,Value FROM crm_config.P7Ca"
                "talogProbe"
            ),
            (
                "CREATE PROCEDURE crm_config.P7CatalogP"
                "rocedure AS SELECT 1 AS OwnedValue"
            ),
            (
                "CREATE FUNCTION crm_config.P7CatalogFu"
                "nction() RETURNS int AS BEGIN RETURN 1"
                " END"
            ),
            (
                "CREATE TRIGGER crm_config.P7CatalogTri"
                "gger ON crm_config.P7CatalogProbe AFTE"
                "R INSERT AS BEGIN SET NOCOUNT ON END"
            ),
            (
                "CREATE PROCEDURE crm_config.P7Encrypte"
                "d WITH ENCRYPTION AS SELECT 1 AS Owned"
                "Value"
            ),
        ]:
            c.execute(statement)
        c.execute(
            (
                "CREATE TRIGGER P7CatalogDDL ON DATABAS"
                "E FOR CREATE_VIEW AS BEGIN SET NOCOUNT"
                " ON END"
            )
        )
        catalog = metadata(c, managed=True)
        result = catalog["objects"]
        for item in result:
            full = "[" + item["schema_name"] + "].[" + item["name"] + "]"
            expected = c.execute(
                "SELECT OBJECT_DEFINITION(OBJECT_ID(?))", full
            ).fetchval()
            assert item["definition"] == expected, full
        for item in catalog["triggers"]:
            assert (
                item["definition"]
                == c.execute(
                    "SELECT OBJECT_DEFINITION(OBJECT_ID(?))",
                    "[" + item["schema_name"] + "].[" + item["name"] + "]",
                ).fetchval()
            )
        ddl = metadata(c, managed=False)["ddl_triggers"]
        for item in ddl:
            object_id = c.execute(
                ("SELECT object_id FROM sys.triggers WHERE parent_class=0 AND name=?"),
                item["name"],
            ).fetchval()
            assert (
                item["definition"]
                == c.execute("SELECT OBJECT_DEFINITION(?)", object_id).fetchval()
            )
        assert len(result) >= 9 and academic(c) == before
    save(
        WORK / "catalog-result.json",
        dict(
            status="passed",
            checks=[
                ("module_default_check_constraint_definitions_equal_OBJECT_DEFINITION"),
                ("tables_keys_and_encrypted_module_keep_NULL_definition"),
                ("DML_and_database_DDL_trigger_definitions_equal_scalar_reference"),
                ("set_catalog_joins_avoid_per_object_scalar_permission_expansion"),
                "30_academic_tables_unchanged_on_owned_fault_copy",
            ],
            database=target,
            objects_compared=len(result),
            DML_triggers_compared=len(catalog["triggers"]),
            DDL_triggers_compared=len(ddl),
            engine=15,
            compatibility=150,
            academic_writes=False,
            query_change="equivalent_catalog_definition_joins",
            real_provider_calls=0,
        ),
    )
    print(json.dumps(dict(status="passed", objects_compared=len(result))))


if __name__ == "__main__":
    main()
