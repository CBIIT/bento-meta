import re
from string import Template
from copy import deepcopy as clone


def countmaker(max=100):
    return (x for x in range(max))


class entity(object):
    """A property graph Entity. Base class."""
    def __init__(self):
        self.As = None
        self.var = type(self).__name__[0].lower() + str(next(type(self).count))

    def pattern(self):
        """Render entity as a match pattern."""
        pass

    def condition(self):
        """Render entity as a condition (for WHERE, e.g.)."""
        pass

    def Return(self):
        """Render entity as a return value."""
        pass

    def _add_props(self, props):
        if not type(self) == N and not type(self) == R:
            return False
        if not props:
            return True
        if type(props) == P:
            props.entity = self
            self.props[props.handle] = props
        elif type(props) == list:
            for p in props:
                p.entity = self
            for p in props:
                self.props[p.handle] = p
        elif type(props) == dict:
            for hdl in props:
                self.props[hdl] = P(handle=hdl, value=props[hdl])
                self.props[hdl].entity = self
        else:
            raise RuntimeError("Can't interpret props arg '{}'".format(props))
        return True


class N(entity):
    """A property graph Node."""
    count = countmaker()

    def __init__(self, label=None, props=None, As=None):
        super().__init__()
        self.props = {}
        self.label = label
        self._add_props(props)
        self.As = As

    def relate_to(self, r, n):
        # always obj --> arg direction
        return r.relate(self, n)

    def pattern(self):
        ret = ",".join([p.pattern() for p in
                        self.props.values() if p.pattern()])
        if (len(ret)):
            ret = " {"+ret+"}"
        if self.label:
            ret = "({}:{}{})".format(self.var, self.label, ret)
        else:
            ret = "({}{})".format(self.var, ret)
        return ret

    def condition(self):
        return [p.condition() for p in self.props.values()]

    def Return(self):
        ret = " as {}".format(self.As) if self.As else ""
        ret = "{}{}".format(self.var, ret)
        return ret


class R(entity):
    """A property graph Relationship or edge."""
    count = countmaker()

    def __init__(self, Type=None, props=None, As=None):
        super().__init__()
        self.props = {}
        self.Type = Type
        self._add_props(props)
        self.As = As

    # n --> m direction
    def relate(self, n, m):
        return T(n, self, m)

    def pattern(self):
        ret = ",".join([p.pattern() for p in
                        self.props.values() if p.pattern()])
        if (len(ret)):
            ret = " {"+ret+"}"
        if self.Type:
            ret = "-[{}:{}{}]-".format(self.var, self.Type, ret)
        else:
            ret = "-[{}{}]-".format(self.var, ret)
        return ret

    def condition(self):
        return [p.condition() for p in self.props.values()]

    def Return(self):
        ret = " as {}".format(self.As) if self.As else ""
        ret = "{}{}".format(self.var, ret)
        return ret


class N0(N):
    """Completely anonymous node ()."""
    def __init__(self):
        super().__init__()
        self.var = None

    def pattern(self):
        return "()"

    def Return(self):
        return None


class R0(R):
    """Completely anonymous relationship -[]-, i.e. --"""
    def __init__(self):
        super().__init__()
        self.var = None

    def pattern(self):
        return "--"

    def Return(self):
        return None


class P(entity):
    """A property graph Property."""
    count = countmaker()

    def __init__(self, handle, value=None, As=None):
        super().__init__()
        self.handle = handle
        self.value = value
        self.As = As
        self.entity = None

    def pattern(self):
        if self.value:
            if not type(self.value) == str:
                return "{}:{}".format(self.handle, str(self.value))
            elif re.match("^\\s*[$]", self.value):
                return "{}:{}".format(self.handle, self.value)
            else:
                return "{}:'{}'".format(self.handle, self.value)
        else:
            return None

    def condition(self):
        if self.value and self.entity:
            if not type(self.value) == str:
                return "{}.{} = {}".format(self.entity.var, self.handle,
                                         str(self.value))
            elif re.match("^\\s*[$]", self.value):
                return "{}.{} = {}".format(self.entity.var, self.handle,
                                         self.value)
            else:
                return "{}.{} = '{}'".format(self.entity.var, self.handle,
                                           self.value)
        else:
            return None

    def Return(self):
        ret = " as {}".format(self.As) if self.As else ""
        if self.entity:
            return "{}.{}{}".format(self.entity.var, self.handle, ret)
        else:
            return None


class T(entity):
    """A property graph Triple; i.e., (n)-[r]->(m)."""
    count = countmaker()

    def __init__(self, n, r, m):
        super().__init__()
        self._from = n
        self._to = m
        self._edge = r

    def pattern(self):
        return self._from.pattern()+self._edge.pattern()+">"+self._to.pattern()

    def condition(self):
        return self.pattern()

    def Return(self):
        return None


def _as(ent, alias):
    """Return copy of ent with As alias set."""
    if isinstance(ent, T):
        return ent
    ret = clone(ent)
    ret.As = alias
    return ret


def _plain(ent):
    """Return entity without properties."""
    ret = None
    if isinstance(ent, (N, R)):
        ret = clone(ent)
        ret.props = {}
    elif isinstance(ent, P):
        ret = clone(ent)
        ret.value = None
    elif isinstance(ent, T):
        ret = clone(ent)
        ret._from.props = {}
        ret._to.props = {}
        ret._edge.props = {}
    else:
        return ent
    return ret


def _anon(ent):
    """Return entity without variable name."""
    ret = clone(ent)
    ret.var = ""
    return ret

def _var_only(ent):
    """Return entity without label or type."""
    ret = None
    if isinstance(ent, (N, R)):
        ret = clone(ent)
        if hasattr(ret, "label"):
            ret.label = None
        if hasattr(ret, "Type"):
            ret.Type = None
    elif isinstance(ent, T):
        ret = clone(ent)
        ret._from.label = None
        ret._to.label = None
        # leave the edge type alone in a triple...
    else:
        return ent
    return ret


def _pattern(ent):
    return ent.pattern()


def _condition(ent):
    return ent.condition()


def _return(ent):
    return ent.Return()


class Clause(object):
    def __init__(self, template, context, joiner, *args, **kwargs):
        self.template = template.upper()
        self.context = context
        self.joiner = joiner
        self.args = list(args)
        self.kwargs = kwargs

    def __str__(self):
        return self.template.substitute(
            slot1=self.joiner.join([self.context(x) for x in self.args])
            )


class Match(Clause):
    """Create a MATCH clause with the arguments."""
    def __init__(self, *args):
        super().__init__(
            template=Template("MATCH $slot1 "),
            context=_pattern,
            joiner=", ",
            *args
            )


class Where(Clause):
    """Create a WHERE clause with the arguments
    (joining conditions with 'op')."""
    def __init__(self, *args, op='AND'):
        super().__init__(
            template=Template("WHERE $slot1 "),
            context=_condition,
            joiner=" {} ".format(op),
            *args, op=op)


class Return(Clause):
    """Create a RETURN clause with the arguments."""
    def __init__(self, *args):
        super().__init__(
            template=Template("RETURN $slot1"),
            context=_return,
            joiner=", ",
            *args)


class Statement(object):
    """Create a Neo4j statement comprised of clauses (and strings) in order."""
    def __init__(self, *args, terminate=False):
        self.clauses = args
        self.terminate = terminate

    def __str__(self):
        ret = " ".join([str(x) for x in self.clauses])
        if self.terminate:
            ret = ret+";"
        return ret
