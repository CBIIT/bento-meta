"""
mdb.searchable
Subclass of `class:bento_meta.mdb.MDB` to support searching fulltext indices on an MDB
Note: certain fulltext indexes on certain MDB nodes and properties must be present in
the Neo4j instance:
- nodeHandle
- propHandle
- termValue
- termDefn
- termValueDefn

"""

from typing import Any

from bento_meta.mdb import MDB, read_txn_data


class SearchableMDB(MDB):
    """:class:`bento_meta.mdb.MDB` subclass for searching fulltext indices on an MDB."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize a :class:`SearchableMDB` object."""
        super().__init__(uri=uri, user=user, password=password)
        self.ftindexes = {}
        with self.driver.session() as s:
            result = s.run("call db.indexes")
            for rec in result:
                if rec["type"] == "FULLTEXT":
                    self.ftindexes[rec["name"]] = {
                        "entity_type": rec["entityType"],
                        "entities": rec["labelsOrTypes"],
                        "properties": rec["properties"],
                    }

    def available_indexes(self) -> dict[str, dict[str, list[str]]]:
        """
        Fulltext indexes present in database.

        Returns:
            Dict mapping index_name to dict with entity_type (NODE|RELATIONSHIP),
            entities ([labels]), properties ([[props]]).
        """
        return self.ftindexes

    @read_txn_data  # type: ignore[reportArgumentType]
    def query_index(
        self,
        index: str,
        qstring: str,
        skip: str | None = None,
        limit: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Query a named fulltext index of nodes or relationships.

        Args:
            index: Name of the fulltext index to query.
            qstring: Lucene query string.
            skip: Number of results to skip.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with ent (entity dict), label, score (lucene score).
        """
        if index not in self.ftindexes:
            msg = f"Index with name '{index}' not found"
            raise RuntimeError(msg)
        tipe = ""
        if self.ftindexes[index]["entity_type"] == "NODE":
            tipe = "queryNodes"
        elif self.ftindexes[index]["entity_type"] == "RELATIONSHIP":
            tipe = "queryRelationships"
        else:
            msg = "Wha?"
            raise RuntimeError(msg)
        thing = self.ftindexes[index]["entity_type"].lower()
        qry = (
            "call db.index.fulltext.{tipe}($name, $query) "
            "yield {thing}, score "
            "return {thing} as ent, head(labels({thing})) as label, score "
            "{skip} {limit} "
        ).format(
            tipe=tipe,
            thing=thing,
            skip="SKIP $skip" if skip else "",
            limit="LIMIT $limit" if limit else "",
        )
        parms = {"name": index, "query": qstring}
        if skip:
            parms["skip"] = skip
        if limit:
            parms["limit"] = limit
        return (qry, parms)  # type: ignore[reportReturnType]

    def search_entity_handles(
        self,
        qstring: str,
    ) -> dict[str, list[dict[str, Any]]] | None:
        """
        Fulltext search of qstring over node, relationship, and property handles.

        Args:
            qstring: Lucene query string.

        Returns:
            Dict with nodes, relationships, properties, each containing list of dicts
            with ent (entity dict) and score (lucene score).
        """
        result = self.query_index("entityHandle", qstring)
        if not result:
            return None
        plural = {
            "node": "nodes",
            "relationship": "relationships",
            "property": "properties",
        }
        ret = {"nodes": [], "relationships": [], "properties": []}
        for item in result:
            ret[plural[item["label"]]].append(
                {"ent": item["ent"], "score": item["score"]}
            )
        return ret

    def search_terms(
        self,
        qstring: str,
        *,
        search_values: bool = True,
        search_definitions: bool = True,
    ) -> list[dict[str, Any]] | None:
        """
        Fulltext search for qstring over terms, by value, definition, or both (default).

        Args:
            qstring: Lucene query string.
            search_values: If True, search term values.
            search_definitions: If True, search term definitions.

        Returns:
            List of dicts with ent (term dict) and score (lucene score).
        """
        index = {
            True: {True: "termValueDefn", False: "termDefn"},
            False: {True: "termValue", False: None},
        }
        return self.query_index(index[search_definitions][search_values], qstring)
