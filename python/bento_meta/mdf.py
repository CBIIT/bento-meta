"""
bento_meta.mdf
==============

This module contains :class:`MDF`, a class for reading a graph data model in
Model Description Format into a :class:`bento_meta.model.Model` object, and 
writing the opposite way.

"""
import sys
from bento_meta.model import Model
from bento_meta.entity import ArgError, CollValue
from bento_meta.objects import (
    Node,
    Edge,
    Property,
    Term,
    ValueSet,
    Tag,
)
import re
import yaml
from yaml.constructor import ConstructorError
from yaml.parser import ParserError
import requests
import delfick_project.option_merge as om
from collections import ChainMap
from warnings import warn
from nanoid import generate
import json

# from pdb import set_trace

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
        self.schema = om.MergedOptions()
        self._model = model
        self._commit = _commit
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
        """Load YAML files or open file handles specified in constructor"""
        yloader = yaml.loader.Loader
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
                    f = response.text
                else:
                    f = open(f, "r")
            try:
                yml = yaml.load(f, Loader=yloader)
                self.schema.update(yml)
            except ConstructorError as ce:
                print("YAML constructor failed in '{fn}':\n{e}".format(fn=f.name, e=ce))
                raise ce
            except ParserError as pe:
                print("YAML parser failed in '{fn}':\n{e}".format(fn=f.name, e=pe))
                raise pe
            except Exception:
                raise

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
            for a in ["category", "desc"]:
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
        for ent in ChainMap(self._model.nodes, self._model.edges).values():
            if isinstance(ent, Node):
                pnames = ynodes[ent.handle]["Props"]
                if yunps:
                    pnames.extend(yunps["mayHave"] if yunps.get("mayHave") else [])
                    pnames.extend(yunps["mustHave"] if yunps.get("mustHave") else [])
            elif isinstance(ent, Edge):
                # props elts appearing Ends hash take
                # precedence over Props elt in the
                # handle's hash
                (hdl, src, dst) = ent.triplet
                [end] = [
                    e
                    for e in yedges[hdl]["Ends"]
                    if e["Src"] == src and e["Dst"] == dst
                ]
                pnames = end.get("Props") or yedges[hdl].get("Props")
                if yurps:
                    pnames.extend(yurps["mayHave"] if yurps.get("mayHave") else [])
                    pnames.extend(yurps["mustHave"] if yurps.get("mustHave") else [])
            else:
                raise AttributeError(
                    "unhandled entity type {type} for properties".format(
                        type=type(ent).__name__
                    )
                )
            if pnames:
                for pname in pnames:
                    ypdef = ypropdefs.get(pname)
                    if not ypdef:
                        warn(
                            "property '{pname}' does not have a corresponding propdef".format(
                                pname=pname
                            )
                        )
                        break
                    init = {"handle": pname,
                            "model": self.handle,
                            "_commit": self._commit}
                    if ypdef.get("Type"):
                        init.update(self.calc_value_domain(ypdef["Type"]))
                    elif ypdef.get("Enum"):
                        init.update(self.calc_value_domain(ypdef["Enum"]))
                    else:
                        init["value_domain"] = Property.default("value_domain")
                    prop = self._model.add_prop(ent, init)
                    ent.props[prop.handle] = prop
                    if ypdef.get("Tags"):
                        for t in ypdef["Tags"]:
                            prop.tags[t] = Tag({"key": t,
                                                "value": ypdef["Tags"][t],
                                                "_commit": self._commit})
        return self._model

    def calc_value_domain(self, typedef):
        if isinstance(typedef, dict):
            if typedef.get("pattern"):
                return {"value_domain": "regexp", "pattern": typedef["pattern"]}
            elif typedef.get("units"):
                return {
                    "value_domain": typedef.get("value_type"),
                    "units": ";".join(typedef.get("units")),
                }
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
            if re.match("^(?:https?|bolt)://", typedef[0]):  # looks like url
                vs.url = typedef[0]
            else:  # an enum
                for t in typedef:
                    vs.terms[t] = Term({"value": t, "_commit": self._commit})
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

            if node.category:
                mdf_node["Category"] = node.category
            if node.nanoid:
                mdf_node["NanoID"] = node.nanoid
            if node.desc:
                mdf_node["Desc"] = node.desc
        for rl in sorted(model.edges):
            edge = model.edges[rl]
            mdf_edge = {}
            mdf["Relationships"][edge.handle] = mdf_edge
            mdf_edge["Mul"] = edge.multiplicity or Edge.default("multiplicity")
            if edge.tags:
                mdf_edge["Tags"] = {}
                for t in edge.tags:
                    mdf_edge["Tags"][t] = edge.tags[t].value
            if edge.is_required:
                mdf_edge["Req"] = True
            if edge.props:
                mdf_edge["Props"] = [prop for prop in sorted(edge.props)]
            if edge.nanoid:
                mdf_edge["NanoID"] = edge.nanoid
            if edge.desc:
                mdf_edge["Desc"] = edge.desc
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
