"""
bento_meta.util.cypher.entities

Representations of cypher nodes, relationships, properties, paths
"""
import re
from pdb import set_trace
from bento_meta.util.cypher.functions import Func
from copy import deepcopy as clone


def countmaker(max=10000):
    return (x for x in range(max))


class Entity(object):
    """A property graph Entity. Base class."""
    def __init__(self):
        self.As = None
        ct = None
        try:
            ct = next(type(self).count)
        except StopIteration:
            type(self)._reset_counter()
            ct = next(type(self).count)
        self.var = type(self).__name__[0].lower() + str(ct)

    @classmethod
    def _reset_counter(cls):
        cls.count = countmaker()

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

    def __init__(self, Type=None, props=None, As=None, _dir='_right'):
        super().__init__()
        self.props = {}
        self.Type = Type
        self._add_props(props)
        self._join = []
        self._dir = _dir
        self.As = As

    # n --> m direction
    def relate(self, n, m):
        return T(n, self, m) if self._dir == '_right' else T(m, self, n)

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

class VarLenR(R):
    """Variable length property graph Relationship or edge."""
    def __init__(self,
        min_len: int = -1,
        max_len: int = -1, 
        Type=None, props=None, As=None, _dir='_right'):
        super().__init__()
        self.props = {}
        self.Type = Type
        self._add_props(props)
        self.min_len = min_len
        self.max_len = max_len

    def pattern(self):
        ret = ",".join([p.pattern() for p in
                        self.props.values() if p.pattern()])
        var_len = "*"
        if self.min_len < 0:
            min_len_str = ""
        else:
            min_len_str = str(self.min_len)
        if self.max_len < 0:
            max_len_str = ""
        else:
            max_len_str = str(self.max_len)
        if min_len_str or max_len_str:
            var_len += f"{min_len_str}..{max_len_str}"
        if len(ret):
            ret = " {"+ret+"}"
        if self.Type:
            ret = f"-[:{self.Type}{ret}{var_len}]-"
        else:
            ret = f"-[{ret}{var_len}]-"
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
    parameterize = False

    def __init__(self, handle, value=None, As=None):
        super().__init__()
        self.handle = handle
        self.value = value
        self.As = As
        self.entity = None
        self.param = {self.var: value} if value else None

    def pattern(self):
        if self.value:
            if not self.parameterize:
                if not type(self.value) == str:
                    return "{}:{}".format(self.handle, str(self.value))
                elif re.match("^\\s*[$]", self.value):  # a parameter
                    return "{}:{}".format(self.handle, self.value)
                else:
                    return "{}:'{}'".format(self.handle, self.value)
            else:
                return "{}:${}".format(self.handle, self.var)
        else:
            return None

    def condition(self):
        if self.value and self.entity:
            if not self.parameterize:
                if not type(self.value) == str:
                    return "{}.{} = {}".format(self.entity.var, self.handle,
                                               str(self.value))
                elif re.match("^\\s*[$]", self.value):  # a parameter
                    return "{}.{} = {}".format(self.entity.var, self.handle,
                                               self.value)
                else:
                    return "{}.{} = '{}'".format(self.entity.var, self.handle,
                                                 self.value)
            else:
                return "{}.{} = ${}".format(self.entity.var, self.handle,
                                            self.var)
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

    def edges(self):
        return [self.edge()]

    def pattern(self):
        return self._from.pattern()+self._edge.pattern()+">"+self._to.pattern()

    def condition(self):
        return self.pattern()

    def Return(self):
        return [x.Return() for x
                in (self._from, self._edge, self._to) if x.var]

class NoDirT(T):
    """A directionless property graph Triple; i.e., (n)-[r]-(m)."""
    def __init__(self, *args):
        super().__init__(*args)

    def pattern(self):
        return self._from.pattern()+self._edge.pattern()+self._to.pattern()

    def nodes(self):
        return [self._from, self._to]

    def edge(self):
        return self._edge

    def edges(self):
        return [self.edge()]

class G(Entity):
    """A property graph Path.
    Defined as an ordered set of partially overlapping triples."""
    count = countmaker()

    def __init__(self, *args):
        super().__init__()
        self._pattern = None
        self.triples = []
        args = list(args)
        self._create_path(args)

    def _create_path(self, args):
        numargs = len(args)
        scr = []
        while args:
            ent = args.pop(0)
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
                elif isinstance(ent, (T, G)):
                    if not self._append(ent):
                        raise RuntimeError(
                            "Adjacent triples/paths do not overlap, "
                            "at arg position {}.".format(numargs-len(args))
                        )
                    scr = []  # reset parse
                else:
                    raise RuntimeError(
                        "Entity '{}' is not valid at arg position {}."
                        .format(ent, numargs-len(args))
                    )
            elif len(scr) == 1:
                if (isinstance(scr[0], N) and isinstance(ent, R)):
                    scr.append(ent)
                elif isinstance(scr[0], R):
                    if isinstance(ent, N):
                        scr.append(ent)
                    elif isinstance(ent, (T, G)) and scr[0]._join:
                        # may be able to link self to ent with _join hints
                        r = scr[0]
                        n1 = [x for x in self.triples[-1].nodes()
                              if x.label == r._join[0]]
                        n2 = [x for x in ent.nodes() if x.label == r._join[1]]
                        if n1 and n2:
                            t = r.relate(n1[0], n2[0])
                            if not self._append(t):
                                raise RuntimeError("WTF error; this should not fail")
                            if not self._append(ent):
                                raise RuntimeError(
                                    "Found right-hand node but could not append path"
                                    )
                            scr = []  # success
                        else:
                            raise RuntimeError(
                                "Can't find endpoint nodes specified in _join for "
                                "relationship at arg position {}".format(numargs-len(args)-1)
                                )
                    else:
                        raise RuntimeError(
                            "Ends of relationship are ambiguous; relationship "
                            "at arg position {} needs _join hints".format(numargs-len(args)-1)
                            )
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
                    elif isinstance(ent, G):
                        if len(ent.triples) > 1:
                            raise RuntimeError(
                                "Can't create start triple, "
                                "to-node is ambiguous, "
                                "at arg position {}.".format(numargs-len(args))
                            )
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
                    if not self._append(scr[0].relate(self.triples[-1]._to,
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
            if len(scr) == 2 and isinstance(
                    scr[0], R) and isinstance(scr[1], N):
                if len(self.triples) > 1:
                    raise RuntimeError(
                        "Can't create end triple, from-node is ambiguous, "
                        "at arg position {}.".format(numargs-len(args))
                    )
                if not self._append(
                        scr[0].relate(self.triples[-1]._to, scr[1])):
                    raise RuntimeError(
                        "Resulting adjacent triples/paths do not overlap, "
                        "at arg position {}."
                        .format(numargs-len(args))
                    )
            else:
                raise RuntimeError("Args do not define a complete Path.")

    def _append(self, ent):
        def _overlap(s, t):
            if s == t:
                return 0b000
            if isinstance(s, G):
                s = s.triples[-1]
            if isinstance(t, G):
                t = t.triples[0]
            if s._from == t._from or (
                    s._from.var and s._from.var == t._from.var):
                return 0b001
            if s._from == t._to or (
                    s._from.var and s._from.var == t._to.var):
                return 0b010
            if s._to == t._from or (
                    s._to.var and s._to.var == t._from.var):
                return 0b011
            if s._to == t._to or (
                    s._to.var and s._to.var == t._to.var):
                return 0b100
            return -1

        if not isinstance(ent, (T, G)):
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
        elif isinstance(ent, G):
            self.triples.extend(ent.triples)
        return True

    def nodes(self):
        ret = set()
        for t in self.triples:
            ret.add(t._from)
            ret.add(t._to)
        return list(ret)

    def edges(self):
        ret = set()
        for t in self.triples:
            ret.add(t._edge)
        return list(ret)

    def pattern(self):
        def jn(trps, acc, ret):
            if not trps:
                ret.append(acc)
                return ret
            trp = trps.pop(0)
            if not acc:
                return jn(trps, [trp._from, trp._edge, ">", trp._to], ret)
            else:
                if trp._from == acc[0]:
                    acc[0:0] = [trp._to, "<", trp._edge]
                elif trp._from == acc[-1]:
                    acc.extend([trp._edge, ">", trp._to])
                elif trp._to == acc[0]:
                    acc[0:0] = [trp._from, trp._edge, ">"]
                elif trp._to == acc[-1]:
                    acc.extend(["<", trp._edge, trp._from])
                else:
                    ret.append(acc)
                    acc = [trp._from, trp._edge, ">", trp._to]
                return jn(trps, acc, ret)
            pass
        if not self._pattern:
            trps = clone(self.triples)
            grps = jn(trps, [], [])
            pats = []
            for grp in grps:
                pats.append(
                    "".join([x.pattern() if not isinstance(x, str) else x
                             for x in grp])
                    )
            self._pattern = ", ".join(pats)
        return self._pattern

    def condition(self):
        return self.pattern()

    def Return(self):
        s = ()
        for t in self.triples:
            s.add(t._from, t._to)
        return ", ".join([_return(x) for x in s if x.var])

# modifiers


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

def _plain_var(ent):
    """Return entity with only the variable, no label or properties"""
    return _plain(_var(ent))

# rendering contexts


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
