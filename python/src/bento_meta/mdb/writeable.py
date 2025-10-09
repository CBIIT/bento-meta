"""
mdb.writeable: subclass of `class:bento_meta.MDB` to support writing to an MDB
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, cast

from typing_extensions import LiteralString

from bento_meta.mdb.mdb import MDB, make_nanoid

if TYPE_CHECKING:
    from collections.abc import Callable

    from neo4j import ManagedTransaction, Record

    from bento_meta.objects import Term


P = ParamSpec("P")


def write_txn(
    func: Callable[Concatenate[WriteableMDB, P], tuple[str, dict[str, Any] | None]],
) -> Callable[Concatenate[WriteableMDB, P], list[Record]]:
    """
    Decorate a query function to run a write transaction based on its query.

    Query function should return a tuple (qry_string, param_dict).

    Args:
        func: The query function to decorate.

    Returns:
        Decorated function that executes a write transaction.
    """

    @wraps(func)
    def wr(self: WriteableMDB, *args: P.args, **kwargs: P.kwargs) -> list[Record]:
        def txn_q(tx: ManagedTransaction) -> list[Record]:
            (qry, parms) = func(self, *args, **kwargs)
            result = tx.run(cast("LiteralString", qry), parameters=parms)
            return list(result)

        with self.driver.session() as session:
            return session.execute_write(txn_q)

    return wr


class WriteableMDB(MDB):
    """:class:`bento_meta.mdb.MDB` subclass for writing to an MDB."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize a :class:`WriteableMDB` object."""
        super().__init__(uri=uri, user=user, password=password)

    @write_txn  # type: ignore[reportArgumentType]
    def put_with_statement(
        self,
        qry: str,
        parms: dict[str, Any] | None = None,
    ) -> list[Record]:
        """Run an arbitrary write statement."""
        if parms is None:
            parms = {}
        if not isinstance(qry, str):
            msg = "qry= must be a string"
            raise TypeError(msg)
        if not isinstance(parms, dict):
            msg = "parms= must be a dict"
            raise TypeError(msg)
        return (qry, parms)  # type: ignore[reportReturnType]

    @write_txn  # type: ignore[reportArgumentType]
    def put_term_with_origin(
        self,
        term: Term,
        commit: str = "",
        _from: int = 1,
    ) -> list[Record]:
        """
        Merge a bento-meta Term object, that has an Origin object set into an MDB.

        If a new term is created, assign a random 6-char nanoid to it.
        The Origin must already be represented in the database.

        Args:
            term: Term object to merge.
            commit: GitHub commit SHA1 associated with the term (if any).
            _from: Source identifier.

        Returns:
            List of Records from the transaction.
        """
        qry = (
            "match (o:origin {name:$o_name, nanoid:$o_id}) "
            "where not exists(o._to) "
            "merge (t:term {"
            "  value:$t_value,"
            "  origin_id:$t_oid,"
            "  origin_version:$t_oversion,"
            "  origin_definition:$t_odefn,"
            "  _from:$from, _commit:$commit}) "
            "merge (o)<-[:has_origin]-(t) "
            "on create set t.nanoid = $t_id "
            "return t.nanoid"
        )
        parms = {
            "o_name": term.origin.name,
            "o_id": term.origin.nanoid,
            "t_value": term.value,
            "t_oid": term.origin_id,
            "t_oversion": term.origin_version,
            "t_odefn": term.origin_definition,
            "t_id": make_nanoid(),
            "commit": commit,
            "from": _from,
        }
        return (qry, parms)  # type: ignore[reportReturnType]
