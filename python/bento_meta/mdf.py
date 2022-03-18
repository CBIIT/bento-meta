"""
bento_meta.mdf
==============

This module contains :class:`MDF`, a class for reading a graph data model in
Model Description Format into a :class:`bento_meta.model.Model` object, and 
writing the opposite way.

"""
import sys
import yaml
from tempfile import TemporaryFile
from MDFValidate.validator import MDFValidator
from bento_meta.model import Model
from bento_meta.entity import ArgError, CollValue
from bento_meta.objects import (
    Node,
    Edge,
    Property,
    Term,
    ValueSet,
    Tag,
    Origin,
)
import re
import requests
from collections import ChainMap
from warnings import warn
from nanoid import generate
import json

from pdb import set_trace

sys.path.extend([".", ".."])

def make_nano():
    return generate(size=6, alphabet="abcdefghijkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789")    

class MDF(object):
    def __init__(self, *yaml_files, handle=None, model=None, _commit=None):
        """Create a :class:`Model` from MDF YAML files/Write a :class:`Model` to YAML
        :param str|file|url *yaml_files: MDF filenames or file objects, 
        in desired merge order
        :param str handle: Handle (name) for the resulting Model
        :param :class:`Model` model: Model to convert to MDF
        :attribute model: the :class:`bento_meta.model.Model` created"""
        if not model and (not handle or not isinstance(handle, str)):
            raise ArgError("arg handle= must be a str - name for model")
        if model and not isinstance(model,Model):
            raise ArgError("arg model= must be a Model instance")
            
        self.files = yaml_files
        self.schema = {}
        self._model = model
        self._commit = _commit
        self._terms = {}
        if model:
            self.handle = model.handle
        else:
            self.handle = handle
        if self.files:
            self.load_yaml()
            self.create_model()
        else:
            if not model:
                warn("No MDF files or model provided to constructor")
                pass

    @property
    def model(self):
        """The :class:`bento_meta.model.Model` object created from the 
           MDF input"""
        return self._model

    def load_yaml(self):
        """Validate and load YAML files or open file handles specified in constructor"""
        vargs = []
        for f in self.files:
            if isinstance(f, str):
                if re.match("(?:file|https?)://", f):
                    response = requests.get(f)
                    if not response.ok:
                        raise ArgError(
                            "Fetching url {} returned code {}".format(
                                response.url, response.status_code
                            )
                        )
                    response.encoding = "utf8"
                    fh = TemporaryFile()
                    for chunk in response.iter_content(chunk_size=128):
                        fh.write(chunk)
                    fh.seek(0)
                    vargs.append(fh)
                else:
                    fh = open(f, "r")
                    vargs.append(fh)
        v = MDFValidator(None, *vargs, verbose=False)
        self.schema = v.load_and_validate_yaml()


    def create_model(self):
        """Create :class:`Model` instance from loaded YAML
        Note: This is brittle, since the syntax of MDF is hard-coded
        into this method."""
        if not self.schema.keys():
            raise ValueError("attribute 'schema' not set - are yamls loaded?")
        if (self.handle):
            self._model = Model(handle=self.handle)
        elif (self.schema.get("Handle")):
            self._model = Model(handle=self.schema["Handle"])
        else:
            raise RuntimeError("Model handle not present in MDF nor provided in args")
        ynodes = self.schema["Nodes"]
        yedges = self.schema["Relationships"]
        ypropdefs = self.schema["PropDefinitions"]
        yunps = self.schema.get("UniversalNodeProperties")
        yurps = self.schema.get("UniversalRelationshipProperties")
        # create nodes
        for n in ynodes:
            yn = ynodes[n]
            init = {"handle": n, "model": self.handle, "_commit": self._commit}
            for a in ["desc","nanoid"]:
                if yn.get(a):
                    init[a] = yn[a]
            node = self._model.add_node(init)
            if yn.get("Tags"):
                for t in yn["Tags"]:
                    node.tags[t] = Tag({"key": t,
                                        "value": yn["Tags"][t],
                                        "_commit": self._commit})
        # create edges (relationships)
        for e in yedges:
            ye = yedges[e]
            for ends in ye["Ends"]:
                init = {
                    "handle": e,
                    "model": self.handle,
                    "src": self._model.nodes[ends["Src"]],
                    "dst": self._model.nodes[ends["Dst"]],
                    "multiplicity": ends.get("Mul")
                    or ye.get("Mul")
                    or Edge.default("multiplicity"),
                    "desc": ends.get("Desc") or ye.get("Desc"),
                    "_commit": self._commit
                }
                edge = self._model.add_edge(init)
                Tags = ye.get("Tags") or ends.get("Tags")
                if Tags:
                    tags = CollValue({}, owner=edge, owner_key="tags")
                    for t in Tags:
                        edge.tags[t] = Tag({"key": t,
                                            "value": Tags[t],
                                            "_commit": self._commit})
        # create properties
        propnames = {}
        for ent in ChainMap(self._model.nodes, self._model.edges).values():
            if isinstance(ent, Node):
                pnames = ynodes[ent.handle]["Props"]
                if yunps:
                    pnames.extend(yunps["mayHave"] if yunps.get("mayHave") else [])
                    pnames.extend(yunps["mustHave"] if yunps.get("mustHave") else [])
                if pnames:
                    propnames[ent] = pnames
            elif isinstance(ent, Edge):
                # props elts appearing Ends hash take precedence over 
                # Props elt in the handle's hash
                (hdl, src, dst) = ent.triplet
                [end] = [
                    e
                    for e in yedges[hdl]["Ends"]
                    if e["Src"] == src and e["Dst"] == dst
                ]
                # note the end-specified props _replace_ the edge-specified props,
                # they are not merged:
                pnames = end.get("Props") or yedges[hdl].get("Props")
                if yurps:
                    pnames.extend(yurps["mayHave"] if yurps.get("mayHave") else [])
                    pnames.extend(yurps["mustHave"] if yurps.get("mustHave") else [])
                if pnames:
                    propnames[ent] = pnames
            else:
                raise AttributeError(
                    "unhandled entity type {type} for properties".format(
                        type=type(ent).__name__
                    )
                )
        prop_of = {}
        for ent in propnames:
            for p in propnames[ent]:
                if prop_of.get(p):
                    prop_of[p].append(ent)
                else:
                    prop_of[p] = [ent]
        for pname in prop_of:
            for ent in prop_of[pname]:
                key = ent.handle+"."+pname
                ypdef = ypropdefs.get(key)
                if not ypdef:
                    key = pname
                    ypdef = ypropdefs.get(pname)
                if not ypdef:
                    warn(
                        "property '{pname}' does not have a corresponding propdef for entity '{handle}'".format(
                        pname=pname, handle=ent.handle
                        )
                    )
                    break
                init = {"handle": pname,
                        "model": self.handle,
                        "_commit": self._commit}
                if ypdef.get("Type"):
                    init.update(self.calc_value_domain(ypdef["Type"],pname))
                elif ypdef.get("Enum"):
                    init.update(self.calc_value_domain(ypdef["Enum"],pname))
                else:
                    warn(
                        "property '{pname}' on entity '{handle}' does not specify "
                        "a data type".format(pname=pname, handle=ent.handle)
                    )
                    init["value_domain"] = Property.default("value_domain")
                reuse = True
                prop = self._model.add_prop(ent, init)
                ent.props[prop.handle] = prop
                if ypdef.get("Tags"):
                    for t in ypdef["Tags"]:
                        prop.tags[t] = Tag({"key": t,
                                            "value": ypdef["Tags"][t],
                                            "_commit": self._commit})
        return self._model

    def calc_value_domain(self, typedef,pname=None):
        if isinstance(typedef, dict):
            if typedef.get("pattern"):
                return {"value_domain": "regexp", "pattern": typedef["pattern"]}
            elif typedef.get("units"):
                return {
                    "value_domain": typedef.get("value_type"),
                    "units": ";".join(typedef.get("units")),
                }
            elif typedef.get("item_type"):
                if (typedef["value_type"] == 'list'):
                    i_domain = self.calc_value_domain(typedef["item_type"])
                    ret = { "value_domain": "list",
                            "item_domain": i_domain["value_domain"]}
                    if i_domain.get("pattern"):
                        ret["pattern"] = i_domain["pattern"]
                    if i_domain.get("units"):
                        ret["units"] = i_domain["units"]
                    if i_domain.get("value_set"):
                        ret["value_set"] = i_domain["value_set"]
                    return ret
                else:
                    warn("MDF type descriptor defines item_type, but value_type is {}, not 'list'".format(typedef["value_type"]))
            elif not typedef:
                warn("MDF type descriptor is null")
            else:
                # punt
                warn(
                    "MDF type descriptor unrecognized: json looks like {}".
                    format(json.dumps(typedef))
                    )
                return {"value_domain": json.dumps(typedef)}
        elif isinstance(typedef, list):  # a valueset: create value set and term objs
            vs = ValueSet({"nanoid": make_nano(), "_commit": self._commit})
            vs.handle = self.handle + vs.nanoid
            # interpret boolean values as strings
            if (isinstance(typedef[0], str) and
                re.match("^(?:https?|bolt)://", typedef[0])):  # looks like url
                    vs.url = typedef[0]
            else:  # an enum
                for t in typedef:
                    if isinstance(t, bool): # stringify booleans in term context
                        t = "True" if t else "False"
                    if not self._terms.get(t):
                        self._terms[t] = Term({"value": t, "_commit": self._commit})
                    vs.terms[t] = self._terms[t]
            return {"value_domain": "value_set", "value_set": vs}
        elif isinstance(typedef, str):
            return {"value_domain": typedef}
        else:
            return {"value_domain": Property.default("value_domain")}

    def write_mdf(self, model=None, file=None):
        """Write a :class:`Model` to a model description file (MDF)
        :param :class:`Model` model: Model to convert (if None, use the model attribute of the MDF object)
        :param str|file file: File name or object to write to (default is None; just return the MDF as dict)
        :returns: MDF as dict"""
        if not model:
            model = self.model
        mdf = {"Nodes":{},
               "Relationships":{},
               "PropDefinitions":{},
               "Terms":{},
               "Handle":model.handle}
        for nd in sorted(model.nodes):
            node = model.nodes[nd]
            mdf_node = {}
            mdf["Nodes"][nd] = mdf_node
            if node.tags:
                mdf_node["Tags"] = {}
                for t in node.tags:
                    mdf_node["Tags"][t] = node.tags[t].value
            mdf_node["Props"] = [prop for prop in sorted(node.props)]

            if node.nanoid:
                mdf_node["NanoID"] = node.nanoid
            if node.desc:
                mdf_node["Desc"] = node.desc
        for rl in sorted(model.edges):
            edge = model.edges[rl]
            mdf_edge = {}
            ends = {}
            if mdf["Relationships"].get(edge.handle):
                mdf_edge = mdf["Relationships"][edge.handle]
            else:
                mdf["Relationships"][edge.handle] = mdf_edge
            ends = {"Src": edge.src.handle,
                    "Dst": edge.dst.handle}
            if mdf_edge.get("Ends"):
                mdf_edge["Ends"].append(ends)
            else:
                mdf_edge["Ends"] = [ends]
            if not mdf_edge.get("Mul"):
                mdf_edge["Mul"] = edge.multiplicity or Edge.default("multiplicity")
            else:
                if mdf_edge["Mul"] != edge.multiplicity:
                    ends["Mul"] = edge.multiplicity
            if edge.tags:
                mdf_edge["Tags"] = {}
                for t in edge.tags:
                    mdf_edge["Tags"][t] = edge.tags[t].value
            if edge.is_required:
                ends["Req"] = True
            if edge.props:
                ends["Props"] = [prop for prop in sorted(edge.props)]
            if edge.nanoid:
                ends["NanoID"] = edge.nanoid
            if edge.desc:
                if not mdf_edge.get("Desc"):
                    mdf_edge["Desc"] = edge.desc
                else:
                    ends["Desc"] = edge.desc
        prnames = []
        props = {}
        for pr in model.props:
            prname = pr[len(pr)-1]
            prnames.append(prname)
            if props.get(prname):
                print("Property name collision at {}".format(pr))
            props[prname] = model.props[pr]
        for prname in sorted(prnames):
            prop = props[prname]
            mdf_prop = {}
            mdf["PropDefinitions"][prname] = mdf_prop
            if prop.tags:
                mdf_prop["Tags"] = {}
                for t in prop.tags:
                    mdf_prop["Tags"][t] = prop.tags[t].value
            if prop.value_domain == "value_set":
                mdf_prop["Enum"] = self.calc_prop_type(prop)
                for t in prop.terms:
                    if t in mdf["Terms"]:
                        print("Term collision at {} (property {})".format(t, prop.handle))
                    mdf["Terms"][t] = {
                        "Definition": prop.terms[t].origin_definition,
                        "Origin": prop.terms[t].origin,
                        "Code": prop.terms[t].origin_id,
                        }
            else:
                mdf_prop["Type"] = self.calc_prop_type(prop)
            if prop.is_required:
                mdf_prop["Req"] = True
            if prop.nanoid:
                mdf_prop["NanoID"] = prop.nanoid
            if prop.desc:
                mdf_prop["Desc"] = prop.desc

        if file:
            fh = file
            if isinstance(file,str):
                fh = open(file, "w")
            yaml.dump(mdf, stream=fh, indent=4)
            
        return mdf

    def calc_prop_type(self,prop):
        if not prop.value_domain:
            return Property.default("value_domain")
        if prop.value_domain == "regexp":
            if not prop.pattern:
                warn("Property {} has 'regexp' value domain, but no pattern specified".format(prop.handle))
                return {"pattern":"^.*$"}
            else:
                return {"pattern":prop.pattern}
        if prop.units:
            return {"value_type":prop.value_domain, "units":prop.units.split(';')}
        if prop.value_domain == "value_set":
            if not prop.value_set:
                warn("Property {} has 'value_set' value domain, but value_set attribute is None".format(prop.handle))
                return "string"
            values = []
            for trm in sorted(prop.terms):
                values.append(trm)
            return values
        # otherwise 
        return prop.value_domain
