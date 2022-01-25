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
    Match, Where, Return,
    Statement
    )

avail_funcs = {x.__name__: x for x in (count, exists, group, And, Or, Not)}


class Query(object):
    paths = {}

    def __init__(self, path):
        self.toks = path.split("/")
        self._match = None
        self._condition = None
        self._return = None

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

        def _walk(ent, toks, pth):
            if not toks or not pth:
                return False  # ERR
            tok = toks[0]
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
                    pad['_node'] = _process_node(pth['_node'])
                elif opn == "_prop":
                    # WARN or ERR if pad.get('_prop') is True
                    # - a parm was already handled in that case
                    pad['_prop'] = _process_prop(pth['_prop'], value=tok)
                elif opn == "_edge":
                    pad['_edge'] = _process_edge(pth['_edge'])
                elif opn == "_return":
                    # pad['_return'] not empty means we're finished
                    if len(tok) == 1:  # we're on the last token
                        pad['_return'] = pth['_return']
                    else:  # more toks to go...
                        pass  # so ignore it
                    pass
                elif opn == "_func":
                    if pth['_func'] in avail_funcs:
                        # the Func subclass:
                        pad['_func'] = avail_funcs[pth['_func']]
                    else:
                        return False  # ERR
                    pass

            # pad ready for operations
            new_ent = None
            if (pad.get('_prop')):  # add props to incoming entity
                ent._add_props(pad['_prop'])
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
            if pad['_return']:
                set_trace()
                return True  # made it
            else:
                if len(toks) == 1:
                    return False  # ERR reached end of toks, no _return found
                else:
                    return _walk(new_ent or ent, toks[1:], pth)

        toks = self.toks
        pth = self.path
        success = _walk(None, toks, pth)
        return success
