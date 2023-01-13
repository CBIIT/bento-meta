"""
bento_meta.util.cypher.clauses

Representations of Cypher statement clauses, statements,
and statement parameters.
"""
from string import Template
from bento_meta.util.cypher.entities import (
    N, R, P, _return, _condition, _pattern
    )
from bento_meta.util.cypher.functions import Func
from pdb import set_trace

class Clause(object):
    """Represents a generic Cypher clause."""
    template = Template("$slot1")
    joiner = ", "

    @staticmethod
    def context(arg):
        return _return(arg)

    def __init__(self, *args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs

    def __str__(self):
        values = []
        for c in [self.context(x) for x in self.args]:
            if isinstance(c, str):
                values.append(c)
            elif isinstance(c, Func):
                values.append(str(c))
            elif isinstance(c, list):
                values.extend([str(x) for x in c])
            else:
                values.append(str(c))
        return self.template.substitute(
            slot1=self.joiner.join(values)
            )


class Match(Clause):
    """Create a MATCH clause with the arguments."""
    template = Template("MATCH $slot1")

    @staticmethod
    def context(arg):
        return _pattern(arg)

    def __init__(self, *args):
        super().__init__(*args)


class Where(Clause):
    """Create a WHERE clause with the arguments
    (joining conditions with 'op')."""
    template = Template("WHERE $slot1")
    joiner = " {} "

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args, op='AND'):
        super().__init__(*args, op=op)
        self.op = op

    def __str__(self):
        values = []
        for c in [self.context(x) for x in self.args]:
            if isinstance(c, str):
                values.append(c)
            elif isinstance(c, Func):
                values.append(str(c))
            elif isinstance(c, list):
                values.extend([str(x) for x in c])
            else:
                values.append(str(c))
        return self.template.substitute(
            slot1=self.joiner.format(self.op).join(values)
            )


class With(Clause):
    """Create a WITH clause with the arguments."""
    template = Template("WITH $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class Create(Clause):
    """Create a CREATE clause with the arguments."""
    template = Template("CREATE $slot1")
    @staticmethod
    def context(arg):
        return _pattern(arg)

    def __init__(self, *args):
        super().__init__(*args)


class Merge(Clause):
    """Create a MERGE clause with the arguments."""
    template = Template("MERGE $slot1")
    @staticmethod
    def context(arg):
        return _pattern(arg)

    def __init__(self, *args):
        super().__init__(*args)

class Remove(Clause):
    """Create a REMOVE clause with the arguments."""
    template = Template("REMOVE $slot1")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        ent = self.args[0]
        item = ""
        sep = ""
        if "prop" in self.kwargs:
            item = self.kwargs["prop"]
            sep = "."
        elif "label" in self.kwargs:
            item = self.kwargs["label"]
            sep = ":"
        return self.template.substitute(
            slot1="{}{}{}".format(self.context(ent),sep,item)
            )
        

class Set(Clause):
    """
    Create a SET clause with the arguments. (Only property arguments matter.)
    """
    template = Template("SET $slot1")

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        values = []
        for c in [self.context(x) for x in self.args if isinstance(x, P)]:
            if isinstance(c, str):
                values.append(c)
            elif isinstance(c, Func):
                values.append(str(c))
            elif isinstance(c, list):
                values.extend([str(x) for x in c])
            else:
                values.append(str(c))
        if 'update' in self.kwargs:
            values = [x.replace("=","+=") for x in values]
        return self.template.substitute(
            slot1=self.joiner.join(values)
            )


class OnCreateSet(Set):
    """Create an ON CREATE SET clause for a MERGE with the arguments."""
    template = Template("ON CREATE SET $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class OnMatchSet(Set):
    """Create an ON CREATE SET clause for a MERGE with the arguments."""
    template = Template("ON MATCH SET $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class Return(Clause):
    """Create a RETURN clause with the arguments."""
    template = Template("RETURN $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class OptionalMatch(Clause):
    """Create an OPTIONAL MATCH clause with the arguments."""
    template = Template("OPTIONAL MATCH $slot1")

    @staticmethod
    def context(arg):
        return _pattern(arg)

    def __init__(self, *args):
        super().__init__(*args)


class Collect(Clause):
    """Create a COLLECT clause with the arguments."""
    template = Template("COLLECT $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class Unwind(Clause):
    """Create an UNWIND clause with the arguments."""
    template = Template("UNWIND $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class As(Clause):
    """Create an AS clause with the arguments."""
    template = Template("AS $slot1")

    def __init__(self, *args):
        super().__init__(*args)


class Statement(object):
    """Create a Neo4j statement comprised of clauses (and strings) in order."""
    def __init__(self, *args, terminate=False, use_params=False):
        self.clauses = args
        self.terminate = terminate
        self.use_params = use_params
        self._params = None

    def __str__(self):
        stash = P.parameterize
        if self.use_params:
            P.parameterize = True
        else:
            P.parameterize = False
        ret = " ".join([str(x) for x in self.clauses])
        if self.terminate:
            ret = ret+";"
        P.parameterize = stash
        return ret

    # def params(self):
    #     if not self._params:
    #         self._params = re.findall("\\$[a-zA-A0-9_]+", str(self))
    #     return self._params
    @property
    def params(self):
        if self._params is None:
            self._params = {}
            for c in self.clauses:
                for ent in c.args:
                    if isinstance(ent, (N, R)):
                        for p in ent.props.values():
                            self._params[p.var] = p.value
                    else:
                        if 'nodes' in vars(type(ent)):
                            for n in ent.nodes():
                                for p in n.props.values():
                                    self._params[p.var] = p.value
                        if 'edges' in vars(type(ent)):
                            for e in ent.edges():
                                for p in e.props.values():
                                    self._params[p.var] = p.value
        return self._params
