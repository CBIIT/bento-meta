"""
bento_meta.util.cypher

Create cypher statements programmatically.
"""

# for values below, need option for producing a $<placeholder> and
# returning a placeholder <-> value mapping
# (alternative to printing values literally in Cypher productions)
# decorator for this: _param( P ) -

import re
from string import Template
from copy import deepcopy as clone


def countmaker(max=100):
    return (x for x in range(max))


class Entity(object):
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


class N(Entity):
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


class R(Entity):
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


class P(Entity):
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


class T(Entity):
    """A property graph Triple; i.e., (n)-[r]->(m)."""
    count = countmaker()

    def __init__(self, n, r, m):
        super().__init__()
        self._from = n
        self._to = m
        self._edge = r

    def nodes(self):
        return [self._from, self._to]

    def edge(self):
        return self._edge

    def pattern(self):
        return self._from.pattern()+self._edge.pattern()+">"+self._to.pattern()

    def condition(self):
        return self.pattern()

    def Return(self):
        return [x.Return() for x in (self._from, self._to)]


def Path(Entity):
    """A property graph Path.
    Defined as an ordered set of partially overlapping triples."""
    def __init__(self, *args):
        super.__init__(*args)
        self.triples = []
        scr = []
        numargs = len(args)
        while args:
            ent = args.pop()
            if len(scr) == 0:
                if isinstance(ent, N):
                    scr.append(ent)
                elif isinstance(ent, R):
                    if self.triples:
                        scr.append(ent)
                    else:
                        raise RuntimeError(
                            "Entity '{}' is not valid at arg position {}."
                            .format(ent, numargs-len(args))
                        )
                elif isinstance(ent, (T, Path)):
                    if not self._append(ent):
                        raise RuntimeError(
                            "Adjacent triples/paths do not overlap, "
                            "at arg position {}.".format(numargs-len(args))
                        )
                else:
                    raise RuntimeError(
                        "Entity '{}' is not valid at arg position {}."
                        .format(ent, numargs-len(args))
                    )
            elif len(scr) == 1:
                if (isinstance(scr[0], N) and isinstance(ent, R)):
                    scr.append(ent)
                elif (isinstance(scr[0], R) and isinstance(ent, N)):
                    scr.append(ent)
                else:
                    raise RuntimeError(
                        "Entity '{}' is not valid at arg position {}."
                        .format(ent, numargs-len(args))
                    )
                pass
            elif len(scr) == 2:
                if isinstance(scr[0], N):
                    success = None
                    if isinstance(ent, N):
                        success = self._append(scr[1].relate(scr[0], ent))
                    elif isinstance(ent, T):
                        success = self._append(scr[1].relate(scr[0],
                                                             ent._from))
                        if success:
                            success = self._append(ent)
                    elif isinstance(ent, Path):
                        success = self._append(
                            scr[1].relate(scr[0], ent.triples[0]._from))
                    else:
                        raise RuntimeError(
                            "Entity '{}' is not valid at arg position {}."
                            .format(ent, numargs-len(args))
                        )
                    if not success:
                        raise RuntimeError(
                            "Resulting adjacent triples/paths do not overlap, "
                            "at arg position {}."
                            .format(numargs-len(args))
                        )
                elif isinstance(scr[0], R):
                    if not self._append(ent.relate(self.triples[-1]._to,
                                                   scr[1])):
                        raise RuntimeError(
                            "Resulting adjacent triples/paths do not overlap, "
                            "at arg position {}."
                            .format(numargs-len(args))
                        )
                scr = []
            else:
                raise RuntimeError("Shouldn't happen.")
        if scr:
            raise RuntimeError("Args do not define a complete Path.")

    def _append(self, ent):
        def _overlap(s, t):
            if s == t:
                return 0b100
            if isinstance(s, Path):
                s = s.triples[-1]
            if isinstance(t, Path):
                t = t.triples[0]
            if s._from == t._from:
                return 0b000
            if s._from == t._to:
                return 0b001
            if s._to == t._from:
                return 0b010
            if s._to == t._to:
                return 0b011
            return -1

        if not isinstance(ent, (T, Path)):
            raise RuntimeError("Can't append a {} to a Path."
                               .format(type(ent).__name__))
        if self.triples:
            ovr = _overlap(self.triples[-1], ent)
            if ovr == 0:
                return True  # same object, skip
            if ovr < 0:
                return False  # Adjacent triples/paths do not overlap
        if isinstance(ent, T):
            self.triples.append(ent)
        elif isinstance(ent, Path):
            self.triples.extend(ent.triples)
        return True


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


def _var(ent):
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
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.pattern()


def _condition(ent):
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.condition()


def _return(ent):
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.Return()


class Func(object):
    template = Template("func(${slot1})")
    joiner = ','

    @staticmethod
    def context(arg):
        return _return(arg)

    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        slot = ""
        if type(self.arg) == list:
            slot = self.joiner.join([self.context(a) for a in self.arg])
        else:
            slot = self.context(self.arg)
        return self.template.substitute(slot1=slot)


class count(Func):
    template = Template("count($slot1)")


class exists(Func):
    template = Template("exists($slot1)")


class Not(Func):
    template = Template("NOT $slot1")

    @staticmethod
    def context(arg):
        return _condition(arg)


class And(Func):
    template = Template("$slot1")
    joiner = " AND "

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args):
        self.arg = list(args)
        super().__init__(self.arg)


class Or(Func):
    template = Template("$slot1")
    joiner = " OR "

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args):
        self.arg = list(args)
        super().__init__(self.arg)


class group(Func):
    template = Template("($slot1)")
    joiner = " "


class is_null(Func):
    template = Template("$slot1 IS NULL")


class is_not_null(Func):
    template = Template("$slot1 IS NOT NULL")


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


class Return(Clause):
    """Create a RETURN clause with the arguments."""
    template = Template("RETURN $slot1")

    def __init__(self, *args):
        super().__init__(*args)


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
