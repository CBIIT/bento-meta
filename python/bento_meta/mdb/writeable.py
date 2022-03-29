"""
mdb.writeable: subclass of `class:bento_meta.MDB` to support writing to an MDB
"""
from functools import wraps
from bento_meta.mdb import make_nanoid
from bento_meta.mdb import MDB

def write_txn(func):
    """Decorates a query function to run a write transaction based
    on its query.
    Query function should return a tuple (qry_string, param_dict)."""
    @wraps(func)
    def wr(self, *args, **kwargs):
        def txn_q(tx):
            (qry,parms)=func(self, *args, **kwargs)
            result = tx.run(qry,parameters=parms)
            return [rec for rec in result]
        with self.driver.session() as session:
            result = session.write_transaction(txn_q)
            return result
    return wr

class WriteableMDB(MDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @write_txn
    def put_with_statement(self, qry, parms={}):
        """Run an arbitrary write statement."""
        if not isinstance(qry, str):
            raise RuntimeError("qry= must be a string")
        if not isinstance(parms, dict):
            raise RuntimeError("parms= must be a dict")
        return (qry, parms)


    @write_txn
    def put_term_with_origin(self, term, commit="", _from=1):
        """Merge a bento-meta Term object, that has an Origin object set,
        into an MDB. If a new term is created, assign a random 6-char nanoid 
        to it. The Origin must already be represented in the database.
        :param Term term: Term object
        :param str commit: GitHub commit SHA1 associated with the term (if any)"""
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
        parms = {"o_name": term.origin.name, "o_id": term.origin.nanoid,
                 "t_value": term.value, "t_oid": term.origin_id,
                 "t_oversion": term.origin_version,
                 "t_odefn": term.origin_definition,
                 "t_id": make_nanoid(), "commit": commit,
                 "from":_from}
        return (qry, parms)
