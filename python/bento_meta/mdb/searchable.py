"""
mdb.searchable
Subclass of `class:bento_meta.mdb.MDB` to support searching fulltext indices on an MDB
Note: certain fulltext indexes on certain MDB nodes and properties must be present in 
the Neo4j instance: 
- entityHandles
- termValue
- termDefn
- termValueDefn

"""
from bento_meta.mdb import read_txn, read_txn_data, read_txn_value
from bento_meta.mdb import MDB
from pdb import set_trace
class SearchableMDB(MDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ftindexes = {}
        with self.driver.session() as s:
            result = s.run("call db.indexes")
            for rec in result:
                if rec['type'] == 'FULLTEXT':
                    self.ftindexes[rec['name']] = {
                        "entity_type":rec['entityType'],
                        "entities":rec['labelsOrTypes'],
                        "properties":rec['properties'],
                    }

    def available_indexes(self):
        """Fulltext indexes present in database. 
        Returns { <index_name> : { entity_type:<NODE|RELATIONSHIP>, entities:[<labels>], 
        properties:[ [<props>] ] } } """
        return self.ftindexes

    @read_txn_data
    def query_index(self, index, qstring, skip=None, limit=None):
        """Query a named fulltext index of nodes or relationships.
        Returns [ {ent:{}, label:<label>, score:<lucene score>} ]."""
        if index not in self.ftindexes:
            raise RuntimeError("Index with name '{}' not found".format(index))
        tipe = ""
        if self.ftindexes[index]['entity_type'] == "NODE":
            tipe = "queryNodes"
        elif self.ftindexes[index]['entity_type'] == "RELATIONSHIP":
            tipe = "queryRelationships"
        else:
            raise RuntimeError("Wha?")
        thing = self.ftindexes[index]['entity_type'].lower()
        qry = (
            "call db.index.fulltext.{tipe}($name, $query) "
            "yield {thing}, score "
            "return {thing} as ent, head(labels({thing})) as label, score "
            "{skip} {limit} "
            ).format(tipe=tipe, thing=thing, skip="SKIP $skip" if skip else "",
                     limit="LIMIT $limit" if limit else "")
        parms = {"name": index, "query": qstring}
        if skip:
            parms['skip'] = skip
        if limit:
            parms['limit'] = limit
        return (qry, parms)

    def search_entity_handles(self, qstring):
        """Fulltext search of qstring over node, relationship, and property handles.
        Returns { node:[ {ent:<entity dict>,score:<lucene score>},... ],
                  relationship:[ <...> ], property:[ <...> ] }"""

        result = self.query_index('entityHandle', qstring)
        if not result:
            return None
        plural = {"node":"nodes", "relationship":"relationships",
                  "property":"properties"}
        ret = {"nodes": [], "relationships": [], "properties": []}
        for item in result:
            ret[plural[item['label']]].append({"ent": item['ent'], "score": item['score']}) 
        return ret

    def search_terms(self, qstring, search_values=True,
                     search_definitions=True):
        """Fulltext for qstring over terms, by value, definition, or both (default).
        Returns [ { ent:<term dict>, score:<lucene score> } ]}"""
        index = {True: {True: 'termValueDefn', False: 'termDefn'},
                 False: {True: 'termValue', False: None}}
        result = self.query_index(index[search_definitions][search_values],
                                  qstring)
        return result
