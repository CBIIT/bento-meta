import sys
import logging
import os.path
sys.path.append("..")
from bento_meta.mdf import MDF
from bento_meta.objects import *
from warnings import warn
# NOTE: the diff class was changed from keeping the final data structure "result"
#       from being 'set' based to being 'list' so that it could be dumped into
#       json structure (which is incompatible with sets)


class Diff:
    """for manipulating the final result data structure when diff models"""

    def __init__(self):
        """sets holds tree of models, as it is parsed"""
        self.sets = {"nodes": {}, "edges": {}, "props": {}}
        # "terms": {} }
        self.clss = {"nodes": Node, "edges": Edge, "props": Property}
        """This will eventually hold the diff results"""
        self.result = {}

    def update_result(self, thing, entk, att, a_att, b_att):
        logging.info(
            "  entering update_result with thing {}, entk {}, att {}".format(
                thing, entk, att
            )
        )
        if thing not in self.result:
            self.result[thing] = {}
        if entk not in self.result[thing]:
            self.result[thing][entk] = {}
        if att not in self.result[thing][entk]:
            self.result[thing][entk][att] = {}
        cleaned_a_att = self.sanitize_empty(a_att)
        cleaned_b_att = self.sanitize_empty(b_att)
        self.result[thing][entk][att]["a"] = cleaned_a_att
        self.result[thing][entk][att]["b"] = cleaned_b_att

    def sanitize_empty(self, item):
        return self.sanitize_empty_list(item)

    def sanitize_empty_set(self, item):
        """an option to turn 'a':set() to 'a':None in final result"""
        if item != set():
            return item
        else:
            return None

    def sanitize_empty_list(self, item):
        """an option to turn 'a': [] to 'a':None in final result"""
        if item != list():
            return item
        else:
            return None

    def valuesets_are_different(self, vs_a, vs_b):
        """see if the group of terms in each value set is different"""

        # compare sets of terms
        # a_att.terms
        #   {'FFPE': <bento_meta.objects.Term object at 0x10..>,
        #    'Snap Frozen': <bento_meta.objects.Term object at 0x10..>}
        # set(a_att.terms)
        #   {'Snap Frozen', 'FFPE'}
        set_of_terms_in_a = set(vs_a.terms)
        set_of_terms_in_b = set(vs_b.terms)

        if set_of_terms_in_a == set_of_terms_in_b:
            return False
        else:
            return True

    def finalize_result(self):
        """adds info for uniq nodes, edges, props from self.sets back to self.result"""
        logging.info("finalizing result")
        for key, value in self.sets.items():
            logging.debug("key {} value {} ".format(key, value))
            logging.debug("sets is {}".format(self.sets))
            logging.debug("result is {}".format(self.result))

            if 0:
                if (value["a"] != set()) or (value["b"] != set()):
                    cleaned_a = self.sanitize_empty(value["a"])
                    cleaned_b = self.sanitize_empty(value["b"])

                    # the key (node/edges/prop) may not be in results (b/c no common diff yet found!)
                    if key not in self.result.keys():
                        self.result[key] = {}
                    self.result[key].update({"a": cleaned_a, "b": cleaned_b})

            if (value["a"] != list()) or (value["b"] != list()):
                cleaned_a = self.sanitize_empty(value["a"])
                cleaned_b = self.sanitize_empty(value["b"])

                # the key (node/edges/prop) may not be in results (b/c no common diff yet found!)
                if key not in self.result.keys():
                    self.result[key] = {}
                self.result[key].update({"a": cleaned_a, "b": cleaned_b})


def diff_models(mdl_a, mdl_b):
    """
    find the diff between two models
    populate the diff results into "sets" and keep some final stuff in result.result
    """
    diff_ = Diff()
    sets = diff_.sets
    clss = diff_.clss

    logging.info("point A")
    # set_trace()

    for thing in sets:
        aset = set(getattr(mdl_a, thing))
        bset = set(getattr(mdl_b, thing))
        sets[thing]["a"] = sorted(list(set(aset - bset)))
        sets[thing]["b"] = sorted(list(set(bset - aset)))
        sets[thing]["common"] = sorted(list(set(aset & bset)))

        logging.debug("ok, where is {} at?".format(thing))
        logging.debug("aset is {}".format(aset))
        logging.debug("bset is {}".format(bset))

        logging.debug(" you want a:{}".format(sets[thing]["a"]))
        logging.debug(" you want b:{}".format(sets[thing]["b"]))

    logging.info("point B")
    # set_trace()

    for thing in sets:
        logging.info("now doing ..{}".format(thing))
        # cls becomes a "Node" object, "Edge" object, etc
        cls = clss[thing]

        simple_atts = [x for x in cls.attspec_ if cls.attspec_[x] == "simple"]
        obj_atts = [x for x in cls.attspec_ if cls.attspec_[x] == "object"]
        coll_atts = [x for x in cls.attspec_ if cls.attspec_[x] == "collection"]

        for entk in sets[thing]["common"]:
            logging.info("...common entk is {}".format(entk))
            a_ent = getattr(mdl_a, thing)[entk]
            b_ent = getattr(mdl_b, thing)[entk]

            # try and see if the simple attributes are the same
            logging.info("...simple")
            for att in simple_atts:
                if getattr(a_ent, att) == getattr(b_ent, att):
                    logging.info("...comparing simple {}".format(getattr(a_ent, att)))
                    logging.info("...comparing simple {}".format(getattr(b_ent, att)))
                    continue
                else:
                    diff_.update_result(
                        thing,
                        entk,
                        att,
                        sorted(getattr(a_ent, att)),
                        sorted(getattr(b_ent, att)),
                    )

            # try and see if the "object" type is the same?
            #     a_att,b_att are things like "valuesets", "properties"
            logging.info("...object")
            for att in obj_atts:
                a_att = getattr(a_ent, att)
                b_att = getattr(b_ent, att)

                if a_att == b_att:  # only if both 'None' *or* is same object
                    continue
                if not a_att or not b_att:  # one is 'None'
                    diff_.update_result(thing, entk, att, sorted(a_att), sorted(b_att))
                    continue

                if type(a_att) == type(b_att):
                    if type(a_att) == ValueSet:  # kludge for ValueSet+Terms
                        if diff_.valuesets_are_different(a_att, b_att):
                            diff_.update_result(
                                thing,
                                entk,
                                att,
                                sorted(list(set(a_att.terms) - set(b_att.terms))),
                                sorted(list(set(b_att.terms) - set(a_att.terms))),
                            )
                    # items are something-other-than valuesets
                    elif getattr(a_att, "handle"):
                        if a_att.handle == b_att.handle:
                            continue
                        else:
                            diff_.update_result(
                                thing, entk, att, sorted(a_att), sorted(b_att)
                            )
                    else:
                        warn(
                            "can't handle attribute with type {}".format(
                                type(a_att).__name__
                            )
                        )
                        logging.warning(
                            "can't handle attribute with type {}".format(
                                type(a_att).__name__
                            )
                        )
                else:
                    diff_.update_result(thing, entk, att, sorted(a_att), sorted(b_att))

            # try and see if the "collection" set is the same?
            logging.info("...collection")
            for att in coll_atts:
                aset = set(getattr(a_ent, att))
                bset = set(getattr(b_ent, att))
                if aset != bset:
                    diff_.update_result(
                        thing,
                        entk,
                        att,
                        sorted(list(set(aset - bset))),
                        sorted(list(set(bset - aset))),
                    )

    logging.info("done")
    diff_.finalize_result()
    return diff_.result


if __name__ == "__main__":
    # m = hashlib.md5();
    # m.update(b"Hey dude");
    # print(m.hexdigest());

    smp_dir = "../tests/samples"
    mdl_a = MDF(os.path.join(smp_dir, "test-model-a.yml"), handle="test")
    mdl_b = MDF(os.path.join(smp_dir, "test-model-b.yml"), handle="test")
    result = diff_models(mdl_a.model, mdl_b.model)
    print(result)
    pass
