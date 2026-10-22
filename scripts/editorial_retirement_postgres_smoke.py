"""Exercise explicit editorial deletion and audit guard on a disposable DB only."""

import asyncio
from uuid import uuid4

import asyncpg

from k_loto.core.config import get_settings
from scripts.server_maintenance import EDITORIAL_RETIREMENT_SQL


async def main() -> None:
    url = str(get_settings().database_url).replace("postgresql+asyncpg:", "postgresql:")
    name = url.rsplit("/", 1)[-1]
    if not name.startswith("k_loto_audit_"):
        raise RuntimeError("Disposable audit database required")
    connection = await asyncpg.connect(url)
    user, publication, business_audit = uuid4(), uuid4(), uuid4()
    try:
        await connection.execute(
            "INSERT INTO users (id,display_name) VALUES ($1,'Editorial smoke')", user
        )
        await connection.execute(
            "INSERT INTO publications (id,author_id,lottery_code,content) "
            "VALUES ($1,$2,'weekly','{}')",
            publication,
            user,
        )
        await connection.execute(
            "INSERT INTO admin_audit_log "
            "(id,admin_user_id,action,entity_type,entity_id) "
            "VALUES ($1,$2,'CREATE','PUBLICATION',$3),"
            "($4,$2,'UPDATE','distribution_draw',$3)",
            uuid4(),
            user,
            publication,
            business_audit,
        )
        await connection.execute(EDITORIAL_RETIREMENT_SQL)
        assert await connection.fetchval("SELECT count(*) FROM publications") == 0
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM admin_audit_log WHERE entity_type='PUBLICATION'"
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM admin_audit_log WHERE id=$1", business_audit
            )
            == 1
        )
        try:
            await connection.execute(
                "DELETE FROM admin_audit_log WHERE id=$1", business_audit
            )
        except asyncpg.RaiseError:
            pass
        else:
            raise AssertionError("Business audit immutability guard lost")
        print("Editorial retirement: scoped deletion and restored audit guard OK")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
