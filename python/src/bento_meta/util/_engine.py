import re
from bento_meta.util.cypher.entities import (  # noqa E402
    N, R, P, N0, R0, G,
    _as, _var, _plain, _anon,
    )

from bento_meta.util.cypher.functions import (
    count, exists, labels, group, And, Or, Not,
    )
from bento_meta.util.cypher.clauses import (
    Match, Where, With, Return,
    Statement
    )
from pdb import set_trace  # noqa E402

avail_funcs = {x.__name__: x for x in (count, exists, labels, group, And, Or, Not)}


class _engine(object):
    paths = None

    def __init__(self, use_params=True):
        self.use_params = use_params
        self.error = None
        self.statement = None
        self.params = None
        self.key = ""
        self.path_id = None
        pass

    @classmethod
    def set_paths(cls, paths):
        cls.paths = paths

    def parse(self, toks):
        toks = toks
        pth = self.paths
        return self._walk(None, toks, pth)

    def _process_node(self, block):
        ret = None
        if isinstance(block, str):
            if block == '_var':
                ret = N()
            else:
                ret = N(label=block)
        elif isinstance(block, dict):
            if not block['_label']:
                self.error = {
                    "description": "_node block requires _label key",
                    "block": block,
                    }
                return False
            ret = N(label=block['_label'])
            if block.get('_prop'):
                ret._add_props(self._process_prop(block['_prop']))
            if block.get('_edge') and block.get('_node'):
                n = self._process_node(block['_node'])
                e = self._process_edge(block['_edge'])
                ret = G(ret, e, n)
        else:
            self.error = {
                "description": "Can't process _node block",
                "block": block,
                }
            return False
        return ret

    def _process_prop(self, block, value=None):
        ret = None
        if isinstance(block, str):
            ret = P(handle=block,
                    value=value)
        elif (isinstance(block, dict) and
              block.get('_handle') and block.get('_value')):
            ret = P(handle=block['_handle'],
                    value=block['_value'])
        else:
            self.error = {
                "description": "Can't process _prop block",
                "block": block
                }
            return False
        return ret

    def _process_edge(self, block):
        ret = None
        if isinstance(block, str):
            ret = R(Type=block)
        elif isinstance(block, dict):
            ret = R(Type=block['_type'])
            if block.get('_dir'):
                ret._dir = block.get('_dir')
            if block.get('_join'):
                # when an edge connects two complex paths
                # define the nodes on the incoming path and new path
                # to link with this edge
                ret._join = block['_join']
        else:
            self.error = {
                "description": "Can't process _edge block",
                "block": block,
                }
            return False
        return ret

    def _process_func(self, block):
        ret = {}
        if isinstance(block, str):
            as_ = re.split("@",block)
            ret['_func'] = as_[0]
            if len(as_) > 1:
                as_ = as_[1]
            else:
                as_ = None
            if ret['_func'] in avail_funcs:
                # the Func subclass:
                ret['_func'] = avail_funcs[ret['_func']]
                ret['_func_as'] = as_
            else:
                self.error = {
                    "description": "Sorry, no cypher function '{}' is currently defined".format(ret['_func']),
                    "block": block,
                    }
                return False  # ERR no such function available
        else:
            self.error = {
                "description": "Block type other than simple string not yet handled for _func",
                "block": block,
                }
            return False
        return ret
                
    def _create_statement(self, ent, pad):
        match_clause = Match(ent)
        ret_clause = None
        a = []
        if isinstance(pad['_return'], str):
            if pad['_return'] == '_items':
                if isinstance(ent, (N, R)):
                    ret_clause = Return(ent)
                else:
                    ret_clause = Return(*ent.nodes())
            else:
                if isinstance(ent, N) and ent.label == pad['_return'] and ent.var:
                    a.append(ent)
                elif isinstance(ent, R) and ent.Type == pad['_return'] and ent.var:
                    a.append(ent)
                else:
                    a.extend([x for x in ent.nodes()
                              if x.label == pad['_return'] and x.var])
                if not a:
                    self.error = {
                        "description": "No named node to return with label '{}'".format(pad['_return']),
                        "ent": ent,
                        "pad": pad,
                        }
                    return False
                else:
                    ret_clause = Return(*a)
        elif isinstance(pad['_return'], dict):
            retblock = pad['_return']
            if retblock.get('_path_id'):
                self.path_id = retblock['_path_id']
            if retblock.get('_nodes'):
                # assume is list-valued
                if not isinstance(retblock['_nodes'], list):
                    self.error = {
                        "description": '_nodes key must point to a list',
                        "ent": ent,
                        "pad": pad,
                        }
                    return False
                labels = {x[0]:x[1] for x in [re.split("@",y)+[None] for y in retblock['_nodes']]}
                if '*' in labels:
                    a.append('*')
                elif (isinstance(ent, N) and ent.var):
                    if ent.label in labels:
                        if labels[ent.label]:
                            a.append(_as(ent, labels[ent.label]))
                        else:
                            a.append(ent)
                    if '_var' in labels and ent == pad['_var']:
                        if labels['_var']:
                            a.append(_as(ent, labels['_var']))
                        else:
                            a.append(ent)
                else:
                    for n in ent.nodes():
                        if n.label in labels and n.var:
                            if labels[n.label]:
                                a.append(_as(n, labels[n.label]))
                            else:
                                a.append(n)
                        if '_var' in labels and n == pad['_var']:
                            if labels['_var']:
                                a.append(_as(n, labels['_var']))
                            else:
                                a.append(n)
                                        
            if retblock.get('_edges'):
                if not isinstance(retblock['_edges'], list):
                    self.error = {
                        "description": '_edges key must point to a list',
                        "ent": ent,
                        "pad": pad,
                        }
                    return False
                types = {x[0]:x[1] for x in [re.split("@",y)+[None] for y in retblock['_edges']]}
                if isinstance(ent, R) and ent.var:
                    if ent.Type in types:
                        if types[ent.Type]:
                            _as(ent, types[ent.Type])
                        else:
                            a.append(ent)
                    if '_var' in types and ent == pad['_var']:
                        if types['_var']:
                            a.append(_as(ent, types['_var']))
                        else:
                            a.append(ent)
                else:
                    for e in ent.edges():
                        if e.Type in types and e.var:
                            if types[e.Type]:
                                a.append(_as(e, types[e.Type]))
                            else:
                                a.append(e)
            if not a:
                self.error = {
                    "description": "No named nodes or edges matching the path _return spec",
                    "ent": ent,
                    "pad": pad,
                    }
                return False
            else:
                if retblock.get('_func'):
                    f = self._process_func(retblock['_func'])
                    if not f:
                        return False  # bad _func spec
                    a = [f['_func'](x) for x in a]
                    if f.get('_func_as'):
                        a = [_as(x, f['_func_as']) for x in a]
                ret_clause = Return(*a)
        else:
            self.error = {
                "description": "_return specification not str or dict",
                "ent": ent,
                "pad": pad,
                }
            return False
        self.statement = Statement(match_clause, ret_clause,
                                   use_params=self.use_params)
        self.params = self.statement.params
        return True

    def _walk(self, ent, toks, pth):
        if not toks or not pth:
            self.error = {
                "description": "_walk: Either toks or pth is empty"
                }
            return False
        tok = toks[0]
        pad = {}
        parm = None
        if tok in pth:
            # plain token - shouldn't start with _
            self.key = "/".join([self.key, tok]) if self.key else tok
            pth = pth[tok]
        elif any([x.startswith('$') for x in pth]):
            # parameter
            parm = [x for x in pth if x.startswith('$')][0]
            pth = pth[parm]
            # load pad
            pad['_prop'] = P(handle=parm[1:], value=tok)
            # note that the cache key will be interpreted as a regexp
            self.key = "/".join([self.key, "([a-zA-Z0-9_]+)"]) if self.key else "([a-zA-Z0-9_]+)"
            pass
        else:
            self.error = {
                "description": "Token '{}' not on valid path".format(tok),
                "token": tok
                }
            return False
        # collect/create items req by block in the pad, and then
        # execute operations on these items in standard order below.
        for opn in [x for x in pth if x.startswith('_')]:
            # operations in block
            if opn == "_node":
                if parm:  # processing a parameter
                    pad['_node'] = pth['_node']
                else:
                    pad['_node'] = self._process_node(pth['_node'])
                    if pth['_node'] == '_var':
                        pad['_var'] = pad['_node']
            elif opn == "_edge":
                if parm:  # processing a parameter
                    pad['_edge'] = pth['_edge']
                else:
                    pad['_edge'] = self._process_edge(pth['_edge'])
                    if pth['_edge'] == '_var':
                        pad['_var'] == pad['_edge']
            elif opn == "_prop":
                # WARN or ERR if pad.get('_prop') is True
                # - a parm was already handled in that case
                pad['_prop'] = self._process_prop(pth['_prop'], value=tok)
            elif opn == "_return":
                if len(toks) == 1:  # we're on the last token
                    # pad['_return'] not empty means we're finished
                    pad['_return'] = pth['_return']
                else:  # more toks to go...
                    pass  # so ignore it
                pass
            elif opn == "_func":
                _func = self._process_func(pth['_func'])
                if not _func:
                    return False # bad _func spec
                for k in _func:
                    pad[k] = _func[k]
            pass

        # pad ready for operations
        new_ent = None
        if (pad.get('_prop')):  # add props to incoming entity
            if isinstance(ent, (N, R)):
                ent._add_props(pad['_prop'])
            else:
                if not pad.get('_node') and not pad.get('_edge'):
                    self.error = {
                        "description": "Both _edge and _node must be defined here",
                        "token": tok
                        }
                    return False  # ERR, if incoming is path, need to specify the node which gets the property (by label)
                else:
                    if pad.get('_node'):
                        n = [x for x in ent.nodes()
                             if x.label == pad['_node']]
                        if not n:
                            self.error = {
                                "description": "Node specified by _node is not present",
                                "token": tok
                                }
                            return False  # specified node can't be found in ent
                        else:
                            n[0]._add_props(pad['_prop'])
                            pad['_node'] = None
                            pad['_prop'] = None
                    if pad.get('_edge'):
                        e = [x for x in ent.edges()
                             if x.Type == pad['_edge']]
                        if not e:
                            self.error = {
                                "description": "Edge specified by _edge is not present",
                                "token": tok
                                }
                            return False  # specified edge not found in ent
                        else:
                            e[0]._add_props(pad['_prop'])
                            pad['_edge'] = None
                            pad['_prop'] = None

        if (pad.get('_node')):  # new entity
            new_ent = pad['_node']
        if (pad.get('_edge')):
            if not ent:  # no input entity
                self.error = {
                    "description": "No incoming entity to apply _edge to here",
                    "token": tok
                    }
                return False  # ERR
            if not new_ent:  # no new entity
                self.error = {
                    "description": "No new entity to link to",
                    "token": tok
                    }
                return False  # different ERR
            if isinstance(ent, N) and isinstance(new_ent, N):
                # simple relationship
                new_ent = pad['_edge'].relate(ent, new_ent)
            else:
                new_ent = G(ent, pad['_edge'], new_ent)
        if pad.get('_return'):  # we made it
            if self._create_statement(new_ent or ent, pad):
                return True
            else:
                return False
        else:
            if len(toks) == 1:
                self.error = {
                    "description": "Reached end of path, but found no _return spec",
                    "token": tok
                    }
                return False  # ERR reached end of toks, no _return found
            else:
                return self._walk(new_ent or ent, toks[1:], pth)
