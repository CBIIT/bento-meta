"""
makeq - make a Neo4j query from an endpoint path.
"""
import yaml
# import re
from pdb import set_trace
from bento_meta.util.cypher import (  # noqa E402
    N, R, P, N0, R0, G,
    _as, _var, _plain, _anon,
    count, exists, group, And, Or, Not,
    Match, Where, With, Return,
    Statement
    )

avail_funcs = {x.__name__: x for x in (count, exists, group, And, Or, Not)}


def f(pfx, pth):
    tok = [x for x in pth if x.startswith('$')]
    if not tok:
        tok = [x for x in pth if not x.startswith('_')]
    if not tok:
        print(pfx)
        return
    else:
        if pth.get('_return'):
            print(pfx)
        for t in tok:
            f('/'.join([pfx, t]), pth[t])
        return

class Query(object):
    paths = {}

    def __init__(self, path):
        if path.startswith("/"):
            path = path[1:]
        self.toks = path.split("/")
        self._statement = None
        self._params = {}

    @classmethod
    def set_paths(cls, paths):
        cls.paths = paths
        return True

    @classmethod
    def load_paths(cls, flo):
        p = yaml.load(flo, Loader=yaml.CLoader)
        if p.get('paths'):
            cls.paths = p['paths']
        else:
            cls.paths = p
        return True

    def _parse_toks(self):
        def _process_node(block):
            ret = None
            if isinstance(block, str):
                ret = N(label=block)
            elif isinstance(block, dict):
                if not block['_label']:
                    raise RuntimeError("_node block requires _label key")
                ret = N(label=block['_label'])
                if block.get('_prop'):
                    ret._add_props(_process_prop(block['_prop']))
                if block.get('_edge') and block.get('node'):
                    n = _process_node(block['_node'])
                    e = _process_edge(block['_edge'])
                    ret = G(ret, e, n)
            else:
                raise RuntimeError("Can't process _node block '{}'".
                                   format(block))
            return ret

        def _process_prop(block, value=None):
            ret = None
            if isinstance(block, str):
                ret = P(handle=block,
                        value=value)
            elif (isinstance(block, dict) and
                  block.get('_handle') and block.get('_value')):
                ret = P(handle=pth['_prop']['_handle'],
                        value=pth['_prop']['_value'])
            else:
                raise RuntimeError("Can't process _prop block '{}'".
                                   format(block))
            return ret

        def _process_edge(block):
            ret = None
            if isinstance(block, str):
                ret = R(Type=block)
            elif isinstance(block, dict):
                ret = R(Type=block['_type'])
                if block.get('_dir'):
                    ret._dir = block.get('_dir')
            else:
                raise RuntimeError("Can't process _edge block '{}'".
                                   format(block))
            return ret

        def _create_statement(ent, pad):
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
                        raise RuntimeError(
                            "No named node to return with label '{}'"
                            .format(pad['_return']))
                    else:
                        ret_clause = Return(*a)
            elif isinstance(pad['_return'], dict):
                if pad['_return'].get('_nodes'):
                    if pad['_return']['_nodes'] == '*':
                        a.append('*')
                    elif isinstance(ent, N) and ent.label in pad['_return']['_nodes'] and ent.var:
                        a.append(ent)
                    else:
                        a.extend([x for x in ent.nodes()
                                  if x.label in pad['_return']['_nodes'] and x.var])
                if pad['_return'].get('_edges'):
                    if isinstance(ent, R) and ent.Type in pad['_return']['edges'] and ent.var:
                        a.append(ent)
                    else:
                        a.extend([x for x in ent.edges()
                                  if x.Type in pad['_return']['_nodes'] and x.var])

                if not a:
                    raise RuntimeError(
                        "No named nodes or edges matching the path "
                        "_return specification")
                else:
                    if pad['_return'].get('_func'):
                        func = avail_funcs[pad['_return']['_func']]
                        a = [func(x) for x in a]
                    ret_clause = Return(*a)
            else:
                raise RuntimeError("_return specification not str or dict")
            self._statement = Statement(match_clause, ret_clause)
            return True
        
        def _walk(ent, toks, pth):
            if not toks or not pth:
                return False  # ERR need non-empty toks and pth
            tok = toks[0]
            if tok == "disease_term" and len(toks) == 1:
                set_trace()
            pad = {}
            parm = None
            if tok in pth:
                # plain key - shouldn't start with _
                pth = pth[tok]
            elif any([x.startswith('$') for x in pth]):
                # parameter
                parm = [x for x in pth if x.startswith('$')][0]
                pth = pth[parm]
                # load pad
                pad['_prop'] = P(handle=parm[1:], value=tok)
                pass
            else:
                # fail
                return False
            # collect/create items req by block in the pad, and then
            # execute operations on these items in standard order below.
            for opn in [x for x in pth if x.startswith('_')]:
                # operations in block
                if opn == "_node":
                    if parm:  # processing a parameter
                        pad['_node'] = pth['_node']
                    else:
                        pad['_node'] = _process_node(pth['_node'])
                elif opn == "_edge":
                    if parm:  # processing a parameter
                        pad['edge'] = pth['edge']
                    else:
                        pad['_edge'] = _process_edge(pth['_edge'])
                elif opn == "_prop":
                    # WARN or ERR if pad.get('_prop') is True
                    # - a parm was already handled in that case
                    pad['_prop'] = _process_prop(pth['_prop'], value=tok)
                elif opn == "_return":
                    if len(toks) == 1:  # we're on the last token
                        # pad['_return'] not empty means we're finished
                        pad['_return'] = pth['_return']
                    else:  # more toks to go...
                        pass  # so ignore it
                    pass
                elif opn == "_func":
                    set_trace()
                    if pth['_func'] in avail_funcs:
                        # the Func subclass:
                        pad['_func'] = avail_funcs[pth['_func']]
                    else:
                        return False  # ERR no such function available
                    pass

            # pad ready for operations
            new_ent = None
            if (pad.get('_prop')):  # add props to incoming entity
                if isinstance(ent, (N,R)):
                    ent._add_props(pad['_prop'])
                else:
                    if not pad.get('_node') and not pad.get('_edge'):
                        return False # ERR, if incoming is path, need to specify the node which gets the property (by label)
                    else:
                        if pad.get('_node'):
                            n = [x for x in ent.nodes()
                                 if x.label == pad['_node']]
                            if not n:
                                return False  # specified node can't be found in ent
                            else:
                                n[0]._add_props(pad['_prop'])
                                pad['_node'] = None
                                pad['_prop'] = None
                        if pad.get('_edge'):
                            e = [x for x in ent.edges()
                                 if x.Type == pad['_edge']]
                            if not e:
                                return False # specified edge not found in ent
                            else:
                                e[0]._add_props(pad['_prop'])
                                pad['_edge'] = None
                                pad['_prop'] = None
                            
            if (pad.get('_node')):  # new entity
                new_ent = pad['_node']
            if (pad.get('_edge')):
                if not ent:  # no input entity
                    return False  # ERR
                if not new_ent:  # no new entity
                    return False  # different ERR
                if isinstance(ent, N) and isinstance(new_ent, N):
                    # simple relationship
                    new_ent = pad['_edge'].relate(ent, new_ent)
                else:
                    new_ent = G(ent, pad['_edge'], new_ent)
            if pad.get('_return'):  # we made it
                _create_statement(new_ent or ent, pad)
                return True
            else:
                if len(toks) == 1:
                    return False  # ERR reached end of toks, no _return found
                else:
                    return _walk(new_ent or ent, toks[1:], pth)

        toks = self.toks
        pth = self.paths
        success = _walk(None, toks, pth)
        set_trace()
        return success
