import sys

sys.path.append('..')
# import hashlib
from bento_meta.mdf import MDF
from bento_meta.objects import *
from bento_meta.entity import Entity
from warnings import warn
from pdb import set_trace

def diff_models(mdl_a, mdl_b):
    set_trace()
    sets = { "nodes": {},
                 "edges": {},
                 "props": {} }
#                 "terms": {} }
    clss  = { "nodes":Node,
                  "edges":Edge,
                  "props":Property }
    result = {}
    def update_result(thing,entk,att,a_att,b_att):
        if not thing in result:
            result[thing]={}
        if not entk in result[thing]:
            result[thing][entk] = {}
        if not att in result[thing][entk]:
            result[thing][entk][att] = {}
        result[thing][entk][att]["a"] = a_att
        result[thing][entk][att]["b"] = b_att
        
    for thing in sets:
        aset = set(getattr(mdl_a,thing))
        bset = set(getattr(mdl_b,thing))
        sets[thing]["a"] = aset- bset
        sets[thing]["b"] = bset-aset
        sets[thing]["common"] = aset & bset
    for thing in sets:
        cls = clss[thing]
        simple_atts =  [ x for x in cls.attspec_ if cls.attspec_[x] == "simple" ]
        obj_atts = [ x for x in cls.attspec_ if cls.attspec_[x] == "object" ]
        coll_atts = [ x for x in cls.attspec_ if cls.attspec_[x] == "collection" ]
        for entk in sets[thing]["common"]:
            a_ent = getattr(mdl_a,thing)[entk]
            b_ent = getattr(mdl_b,thing)[entk]
            for att in simple_atts:
                if getattr(a_ent,att) == getattr(b_ent,att):
                    continue
                else:
                    update_result(thing,entk,att,getattr(a_ent,att),getattr(b_ent,att))
            for att in obj_atts:
                a_att = getattr(a_ent,att)
                b_att = getattr(b_ent,att)
                if a_att == b_att: # only if both 'None'
                    continue
                if not a_att or not b_att: # one is 'None'
                    update_result(thing,entk,att,a_att,b_att)
                    continue
                if type(a_att) == type(b_att):
                    if type(a_att) == ValueSet:  # kludge for ValueSet+Terms
                        set_trace()
                        aset = set(a_att.terms)
                        bset = set(b_att.terms)
                        if (aset != bset):
                            update_result(thing,entk,att,aset-bset,bset-aset)
                    elif getattr(a_att,"handle"):
                        if a_att.handle == b_att.handle:
                            continue
                        else:
                            update_result(thing,entk,att,a_att,b_att)
                    else:
                        warn("can't handle attribute with type {}".format(type(a_att).__name__))
                else:
                    update_result(thing,entk,att,a_att,b_att)
            for att in coll_atts:
                aset = set(getattr(a_ent,att))
                bset = set(getattr(b_ent,att))
                if aset != bset:
                    update_result(thing,entk,att,aset-bset,bset-aset)
    return result

if __name__ == '__main__':
    # m = hashlib.md5();
    # m.update(b"Hey dude");
    # print(m.hexdigest());
    import os.path
    smp_dir = '../tests/samples'
    mdl_a = MDF(os.path.join(smp_dir,"test-model.yml"),handle="test")
    mdl_b = MDF(os.path.join(smp_dir,"test-model-b.yml"),handle="test")
    result = diff_models(mdl_a.model,mdl_b.model)
    print(result)
    pass;
