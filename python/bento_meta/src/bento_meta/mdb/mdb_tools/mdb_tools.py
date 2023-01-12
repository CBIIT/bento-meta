"""
ToolsMDB: subclass of 'WriteableMDB' to support interactions with the MDB.
"""

from pathlib import Path
import csv
from typing import List
import logging
from logging.config import fileConfig

import spacy
from nanoid import generate
from bento_meta.entity import Entity
from bento_meta.mdb import read_txn, read_txn_data, read_txn_value
from bento_meta.mdb.writeable import WriteableMDB, write_txn
from bento_meta.objects import Concept, Predicate, Property, Term
from bento_meta.util.cypher.clauses import Match, Return, Statement
from bento_meta.util.cypher.entities import N, VarLenR, NoDirT

# logging stuff
log_ini_path = Path(__file__).parents[2].joinpath("logs/log.ini")
log_file_path = Path(__file__).parents[2].joinpath(f"logs/{__name__}.log")
fileConfig(log_ini_path, defaults={'logfilename': log_file_path.as_posix()})
logger = logging.getLogger(__name__)


class EntNotFoundError(Exception):
    """Raised when an entity is not found and shouldn't be created"""


def get_entity_type(entity: Entity):
    """returns type of entity"""
    if entity.__class__.__name__.lower() == "edge":
        return "relationship"
    return entity.__class__.__name__.lower()


class ToolsMDB(WriteableMDB):
    """Adds mdb-tools to WriteableMDB"""

    def __init__(self, uri, user, password):
        WriteableMDB.__init__(self, uri, user, password)

    # FIXME: this should interpolate cypher $parameters, not the actual
    # values
    # (use utils.cypher...)
    def get_entity_attrs(self, entity: Entity, output_str: bool = True):
        """
        Returns attributes as str or dict for given entity.

        Param output_as_str parm defaults to True and returns a string
        that is usable in Cypher query as node properties.

        If output_as_str = False, return dict of attributes instead,
        which is used as params of function with write_txn decorator.
        """
        attr_dict = {}
        for key, val in vars(entity).items():
            if val and val is not None and key != "pvt":
                attr_dict[key] = val

        attr_str = "{"
        for key, val in attr_dict.items():
            attr_str += f"{key}: '{val}', "
        attr_str = attr_str[:-2]
        attr_str += "}"

        if not output_str:
            return attr_dict
        return attr_str

    @write_txn
    def detach_delete_entity(self, entity: Entity) -> tuple:
        """
        Remove given Entity node from the database.

        Accepts the following bento-meta Entities:
            Concept, Node, Predicate, Property, Edge, Term
        """
        entity_type = get_entity_type(entity)
        entity_attr_str = self.get_entity_attrs(entity)
        entity_attr_dict = self.get_entity_attrs(entity, output_str=False)

        qry = f"MATCH (e:{entity_type} " f"{entity_attr_str}) DETACH DELETE e"

        logging.info(f"Removing {entity_type} node with with properties: {entity_attr_str}")
        return (qry, entity_attr_dict)

    @read_txn_value
    def get_entity_count(self, entity: Entity) -> tuple:
        """
        Returns count of given entity (w/ its properties) found in MDB.

        If count = 0, entity with given properties not found in MDB.
        If count = 1, entity with given properties is unique in MDB
        If count > 1, more properties needed to uniquely id entity in MDB.
        """
        # if not (term.origin_name and term.value):
        #     raise RuntimeError("arg 'term' must have both origin_name and value")
        entity_type = get_entity_type(entity)
        if entity.nanoid:
            entity_attr_str = "{nanoid:$nanoid}"
            entity_attr_dict = {"nanoid": entity.nanoid}
        else:
            entity_attr_str = self.get_entity_attrs(entity)
            entity_attr_dict = self.get_entity_attrs(entity, output_str=False)

        qry = (
            f"MATCH (e:{entity_type} {entity_attr_str}) "
            "RETURN COUNT(e) as entity_count"
        )

        return (qry, entity_attr_dict, "entity_count")

    @read_txn_value
    def get_triple_count(
        self,
        src_entity: Entity,
        dst_entity: Entity,
        relationship: str,
    ) -> tuple:
        """
        Returns count of given triple, (src)-[rel]->(dst), found in MDB.

        If count = 0, triple with given properties not found in MDB.
        If count = 1, triple with given properties is unique in MDB
        If count > 1, more properties needed to uniquely id triple in MDB.
        """
        src_entity_type = get_entity_type(src_entity)
        dst_entity_type = get_entity_type(dst_entity)

        qry = (
            "MATCH (s:{src_type} {{nanoid:$src_nano}}) "
            "-[:{relationship}]->"
            "(d:{dst_type} {{nanoid: $dst_nano}}) "
            "RETURN COUNT(*) as triple_count".format(
                src_type=src_entity_type,
                dst_type=dst_entity_type,
                relationship=relationship,
            )
        )

        parms = {
            "src_nano": src_entity.nanoid,
            "dst_nano": dst_entity.nanoid,
        }

        return (qry, parms, "triple_count")

    @write_txn
    def create_entity(
        self,
        entity: Entity,
        _commit=None,
    ) -> tuple:
        """Adds given Entity node to database"""
        if not entity.nanoid:
            logging.error("entity has no nanoid")
            raise RuntimeError(
                "Entity needs a nanoid before creating - please set valid entity nanoid. "
                "entity_name.nanoid = mdb_name.get_or_make_nano(entity_name) AFTER "
                "declaring some other entity properties is a good way to do this."
            )
        if _commit:
            entity._commit = _commit
        entity_type = get_entity_type(entity)
        entity_attr_str = self.get_entity_attrs(entity)
        entity_attr_dict = self.get_entity_attrs(entity, output_str=False)

        qry = f"MERGE (e:{entity_type} {entity_attr_str})"

        logging.info(f"Creating new {entity_type} node with properties: {entity_attr_str}")
        return (qry, entity_attr_dict)

    @read_txn_value
    def get_concepts(self, entity: Entity):
        """Returns list of concepts represented by given entity"""
        # if not (term.origin_name and term.value):
        #     raise RuntimeError("arg 'term' must have both origin_name and value")
        entity_type = get_entity_type(entity)

        if entity.nanoid:
            entity_attr_str = "{nanoid:$nanoid}"
            entity_attr_dict = {"nanoid": entity.nanoid}
        else:
            entity_attr_str = self.get_entity_attrs(entity)
            entity_attr_dict = self.get_entity_attrs(entity, output_str=False)

        if entity_type == "term":
            qry = (
                f"MATCH (e:{entity_type} {entity_attr_str}) "
                "-[:represents]->(c:concept) RETURN c.nanoid AS concept"
            )
        else:
            qry = (
                f"MATCH (e:{entity_type} {entity_attr_str}) "
                "-[:has_concept]->(c:concept) RETURN c.nanoid AS concept"
            )
        return (qry, entity_attr_dict, "concept")

    @write_txn
    def create_relationship(
        self,
        src_entity: Entity,
        dst_entity: Entity,
        relationship: str,
        _commit=None,
    ):
        """Adds relationship between given entities in MDB"""
        # gets number of entities in MDB matching given entity (w/ given properties)
        ent_1_count = self.get_entity_count(src_entity)[0]
        ent_2_count = self.get_entity_count(dst_entity)[0]
        # at least one of the given entities doesn't uniquely id a node in the MDB.
        if ent_1_count > 1 or ent_2_count > 1:
            logging.error("Given attributes don't uniquely identify MDB entities.")
            raise RuntimeError(
                "Given entities must uniquely identify nodes in the MDB. Please add "
                "necessary properties to the entity so that it can be uniquely identified."
            )
        # at least one of given entities not found and shouldn't be added
        if ent_1_count < 1 or ent_2_count < 1:
            logging.error("One or more of the given entities aren't in the MDB.")
            raise RuntimeError("One or more of the given entities aren't in the MDB.")
        src_entity_type = get_entity_type(src_entity)
        dst_entity_type = get_entity_type(dst_entity)

        src_attr_str = self.get_entity_attrs(src_entity)
        dst_attr_str = self.get_entity_attrs(dst_entity)
        _commit_str = ""
        if _commit:
            _commit_str = f"{{_commit:'{_commit}'}}"

        # check if triple (ent1)-[relationship]-(ent2) already exists
        trip_count = self.get_triple_count(
            src_entity=src_entity,
            dst_entity=dst_entity,
            relationship=relationship,
        )[0]

        if trip_count > 1:
            logging.error("Relationship exists more than once")
            raise RuntimeError(
                "This relationship exists more than once, check the MDB "
                "instance as this shouldn't be the case."
            )
        elif trip_count == 1:
            logging.warning(
                f"{relationship} relationship already exists between src {src_entity_type} with "
                f"properties: {src_attr_str} to dst {dst_entity_type} with properties: {dst_attr_str}"
            )
            # way to exit out of decorator? maybe can fix w/ upcoming cypher.utils integration
            # for now removing commit str before merging (which won't create an extra relationship)
            qry = (
                "MATCH (s:{src_type} {{nanoid:$src_nano}}), "
                "(d:{dst_type} {{nanoid: $dst_nano}}) "
                "MERGE (s)-[:{relationship}]->(d)".format(
                    src_type=src_entity_type,
                    dst_type=dst_entity_type,
                    relationship=relationship,
                )
            )
            parms = {
                "src_nano": src_entity.nanoid,
                "dst_nano": dst_entity.nanoid,
            }
            return (qry, parms)

        qry = (
            "MATCH (s:{src_type} {{nanoid:$src_nano}}), "
            "(d:{dst_type} {{nanoid: $dst_nano}}) "
            "MERGE (s)-[:{relationship} {commit}]->(d)".format(
                src_type=src_entity_type,
                dst_type=dst_entity_type,
                relationship=relationship,
                commit=_commit_str,
            )
        )

        parms = {
            "src_nano": src_entity.nanoid,
            "dst_nano": dst_entity.nanoid,
        }
        logging.info(
            f"Adding {relationship} relationship between src {src_entity_type} with "
            f"properties: {src_attr_str} to dst {dst_entity_type} with properties: {dst_attr_str}"
        )
        return (qry, parms)

    def link_synonyms(
        self,
        entity_1: Entity,
        entity_2: Entity,
        add_missing_ent_1: bool = False,
        add_missing_ent_2: bool = False,
        _commit=None,
    ):
        """
        Link two synonymous entities in the MDB via a Concept node.

        This function takes two synonymous Entities (as determined by user/SME) as
        bento-meta objects connects them to a Concept node via a 'represents' relationship.

        If one or both doesn't exist in the MDB and add_missing_ent is True they will be added.

        If one or both doesn't uniquely identify a node in the MDB will give error.

        If _commit is set (to a string), the _commit property of any node created is set to
        this value.
        """
        # gets number of entities in MDB matching given entity (w/ given properties)
        ent_1_count = self.get_entity_count(entity_1)[0]
        ent_2_count = self.get_entity_count(entity_2)[0]
        # at least one of the given entities doesn't uniquely id a node in the MDB.
        if ent_1_count > 1 or ent_2_count > 1:
            logging.error("Given entities don't uniquely identify MDB entities")
            raise RuntimeError(
                "Given entities must uniquely identify nodes in the MDB. Please add "
                "necessary properties to the entity so that it can be uniquely identified."
            )
        # entity 1 not found and shouldn't be added
        if ent_1_count < 1 and not add_missing_ent_1:
            logging.error("Entity 1 isn't in the MDB and add_missing_ent_1 is False.")
            raise EntNotFoundError(
                "Entity 1 isn't in the MDB and add_missing_ent_1 is False."
                "Please add the missing entity to the MDB or set add_missing_ent_1 to True."
            )
        # entity 2 not found and shouldn't be added
        if ent_2_count < 1 and not add_missing_ent_2:
            logging.error("Entity 2 isn't in the MDB and add_missing_ent_2 is False.")
            raise EntNotFoundError(
                "Entity 2 isn't in the MDB and add_missing_ent_2 is False."
                "Please add the missing entity to the MDB or set add_missing_ent_2 to True."
            )
        # entity 1 not found and should be added
        if not ent_1_count and add_missing_ent_1:
            self.create_entity(entity_1, _commit=_commit)
        # entity 2 not found and should be added
        if not ent_2_count and add_missing_ent_2:
            self.create_entity(entity_2, _commit=_commit)
        # get any existing concepts and create new concept if none found
        ent_1_concepts = self.get_concepts(entity_1)
        ent_2_concepts = self.get_concepts(entity_2)
        if ent_1_concepts:
            concept = Concept({"nanoid": ent_1_concepts[0]})
        elif ent_2_concepts:
            concept = Concept({"nanoid": ent_2_concepts[0]})
        else:
            concept = Concept({"nanoid": self.make_nano()})
            self.create_entity(concept, _commit=_commit)
        # entities are already connected by a concept
        if not set(ent_1_concepts).isdisjoint(set(ent_2_concepts)):
            concept = set(ent_1_concepts).intersection(set(ent_2_concepts))
            logging.warning(f"Both entities are already connected via Concept {list(concept)[0]}")
            return
        # create specified relationship between each entity and a concept
        if get_entity_type(entity_1) == "term":
            self.create_relationship(entity_1, concept, "represents", _commit=_commit)
            self.create_relationship(entity_2, concept, "represents", _commit=_commit)
        else:
            self.create_relationship(entity_1, concept, "has_concept", _commit=_commit)
            self.create_relationship(entity_2, concept, "has_concept", _commit=_commit)

    def make_nano(self):
        """Generates valid nanoid"""
        return generate(
            size=6,
            alphabet="abcdefghijkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789",
        )

    def _get_prop_nano(self, prop: Entity, node_handle: str):
        """
        Takes Property and Node entities and returns Property nanoid.

        This is used to help uniquely identify a property node in the MDB,
        which requires a node connected via the has_property relationship.
        """
        qry = (
            "MATCH (p:property {handle:$prop_handle, model: $prop_model})"
            "<-[:has_property]-(n:node {handle: $node_handle}) "
            "RETURN p.nanoid as prop_nano"
        )
        parms = {
            "prop_handle": prop.handle,
            "prop_model": prop.model,
            "node_handle": node_handle,
        }
        return (qry, parms, "prop_nano")

    def _get_edge_nano(self, edge: Entity, src_handle: str, dst_handle: str):
        """
        Takes Edge, src node handle, and dst Node handle and returns Edge nanoid.

        This is used to help uniquely identify an edge node in the MDB,
        which requires nodes connected via the has_src and has_dst relationships.
        """
        qry = (
            "MATCH (s:node {handle: $src_handle})<-[:has_src]-"
            "(r:relationship {handle: $edge_handle, model: $edge_model})-"
            "[:has_dst]->(d:node {handle: $dst_handle}) "
            "RETURN r.nanoid as edge_nano"
        )
        parms = {
            "edge_handle": edge.handle,
            "edge_model": edge.model,
            "src_handle": src_handle,
            "dst_handle": dst_handle,
        }
        return (qry, parms, "edge_nano")

    @read_txn_value
    def get_entity_nano(
        self, entity: Entity, extra_handle_1: str = "", extra_handle_2: str = ""
    ) -> tuple:
        """
        Takes an entity and returns its nanoid. If entity requires handles of connected nodes
        for unique identification (Property or Edge), extra_handle_1 and _2 hold these as str.

        Note: If an entity exists in the MDB with the given properties, but doesn't have an
        assigned nanoid for some reason, returns [None] instead of [].
        """
        ent_type = get_entity_type(entity)
        if ent_type == "property":
            if not extra_handle_1:
                logging.error("Property entity doesn't have connected node handle")
                raise RuntimeError(
                    "Property entities require the handle of a node connected via 'has_property' "
                    "for unique identification. Set 'extra_handle_1' to that node handle str."
                )
            return self._get_prop_nano(prop=entity, node_handle=extra_handle_1)
        if ent_type == "relationship":
            if not extra_handle_1 or not extra_handle_2:
                logging.error("Edge entity doesn't have src or dst node handle")
                raise RuntimeError(
                    "Edge entities require the handles of a node connected via "
                    "'has_src' relationship and of a node connected via 'has_dst' "
                    "relationship for unique identification. Set 'extra_handle_1' to "
                    "the src handle and 'extra_handle_2' to the dst handle"
                )
            return self._get_edge_nano(
                edge=entity, src_handle=extra_handle_1, dst_handle=extra_handle_2
            )

        ent_count = self.get_entity_count(entity)[0]
        if ent_count > 1:
            logging.error("Given entities don't uniquely identify MDB entities")
            raise RuntimeError(
                "Given entities must uniquely identify nodes in the MDB. Please add "
                "necesary properties to the entity so that it can be uniquely identified."
            )
        # if ent_count < 1:
        #     raise RuntimeError("Given entity wasn't found in the MDB")

        ent_attr_str = self.get_entity_attrs(entity)
        ent_attr_dict = self.get_entity_attrs(entity, output_str=False)

        qry = f"MATCH (e:{ent_type} {ent_attr_str}) RETURN e.nanoid as ent_nano"

        return (qry, ent_attr_dict, "ent_nano")

    def get_or_make_nano(
        self, entity: Entity, extra_handle_1: str = "", extra_handle_2: str = ""
    ) -> str:
        """Obtains existing entity's nanoid or creates one for new entity."""
        nano_list = self.get_entity_nano(entity, extra_handle_1, extra_handle_2)
        if len(nano_list) > 1:
            logging.error("Given entity doesn't uniquely identify MDB entities")
            raise RuntimeError(
                "More than one entity exists with these properties. Please "
                "add more properties of the desired entity to uniquely ID."
            )
        elif nano_list and not nano_list[0]:
            logging.error("Entity exists but doesn't have nanoid")
            raise RuntimeError(
                "An entity with these properties exists in the MDB but doesn't "
                "have an assigned nanoid for some reason."
            )
        elif nano_list:
            nano = nano_list[0]
            return nano
        nano = self.make_nano()
        return nano

    @read_txn_value
    def get_term_nanos(self, concept: Concept):
        """Returns list of term nanoids representing given concept"""
        if not concept.nanoid:
            logging.error("Concept doesn't have a nanoid")
            raise RuntimeError("arg 'concept' must have nanoid")
        entity_attr_str = self.get_entity_attrs(concept)
        entity_attr_dict = self.get_entity_attrs(concept, output_str=False)
        qry = (
            f"MATCH (t:term)-[:represents]->(c:concept {entity_attr_str}) "
            "RETURN t.nanoid AS term_nano"
        )
        return (qry, entity_attr_dict, "term_nano")

    @read_txn_value
    def get_predicate_nanos(self, concept: Concept):
        """Returns list of predicate nanoids with relationship to given concept"""
        if not concept.nanoid:
            logging.error("Concept doesn't have a nanoid")
            raise RuntimeError("arg 'concept' must have nanoid")
        entity_attr_str = self.get_entity_attrs(concept)
        entity_attr_dict = self.get_entity_attrs(concept, output_str=False)
        qry = (
            f"MATCH (p:predicate)-[r]->(c:concept {entity_attr_str}) "
            "RETURN p.nanoid AS pred_nano"
        )
        return (qry, entity_attr_dict, "pred_nano")

    @read_txn_value
    def get_predicate_relationship(self, concept: Concept, predicate: Predicate):
        """Returns relationship type between given concept and predicate"""
        if not concept.nanoid or not predicate.nanoid:
            logging.error("Concept or Predicate don't have a nanoid")
            raise RuntimeError("args 'concept' and 'predicate' must have nanoid")
        qry = (
            "MATCH (p:predicate {nanoid: $pred_nano})-[r]->(c:concept {nanoid: $con_nano}) "
            "RETURN TYPE(r) as rel_type"
        )
        parms = {"pred_nano": predicate.nanoid, "con_nano": concept.nanoid}
        return (qry, parms, "rel_type")

    def link_concepts_to_predicate(
        self,
        concept_1: Concept,
        concept_2: Concept,
        predicate_handle: str = "exactMatch",
        _commit=None,
    ) -> None:
        """
        Links two synonymous Concepts via a Predicate

        This function takes two synonymous Concepts as objects and links
        them via a Predicate node and has_subject and has_object relationships.
        """
        if not (concept_1.nanoid and concept_2.nanoid):
            logging.error("Concepts don't have a nanoid")
            raise RuntimeError("args 'concept_1' and 'concept_2' must have nanoid")
        valid_predicate_handles = [
            "exactMatch",
            "closeMatch",
            "broader",
            "narrower",
            "related",
        ]
        if predicate_handle not in valid_predicate_handles:
            logging.error(f"Predicate handle: {predicate_handle} not a valid predicate handle")
            raise RuntimeError(
                f"'handle' key must be one the following: {valid_predicate_handles}"
            )
        # create predicate
        new_predicate = Predicate(
            {"handle": predicate_handle, "nanoid": self.make_nano()}
        )
        self.create_entity(new_predicate, _commit=_commit)
        # link concepts to predicate via subject & object relationships
        self.create_relationship(
            new_predicate, concept_1, "has_subject", _commit=_commit
        )
        self.create_relationship(
            new_predicate, concept_2, "has_object", _commit=_commit
        )

    def merge_two_concepts(
        self, concept_1: Concept, concept_2: Concept, _commit=None
    ) -> None:
        """
        Combine two synonymous Concepts into a single Concept.

        This function takes two synonymous Concept as bento-meta objects and
        merges them into a single Concept along with any connected Terms and Predicates.
        """
        if not (concept_1.nanoid and concept_2.nanoid):
            logging.error("Concept doesn't have a nanoid")
            raise RuntimeError("args 'concept_1' and 'concept_2' must have nanoid")
        # get list of terms connected to concept 2
        c2_term_nanos = self.get_term_nanos(concept_2)
        c2_terms = []
        for nano in c2_term_nanos:
            c2_terms.append(Term({"nanoid": nano}))
        # get list of predicates w/ relationship type connected to concept 2
        c2_pred_nanos = self.get_predicate_nanos(concept_2)
        c2_pred_rels = []
        for nano in c2_pred_nanos:
            pred = Predicate({"nanoid": nano})
            rel = self.get_predicate_relationship(concept_2, pred)[0]
            c2_pred_rels.append([pred, rel])
        # delete concept 2
        self.detach_delete_entity(concept_2)
        # connect terms from deleted (c2) to remaining concept (c1)
        for term in c2_terms:
            self.create_relationship(term, concept_1, "represents", _commit=_commit)
        # connect predicates from deleted (c2) to remaining concept (c1)
        for pred_rel in c2_pred_rels:
            c2_pred = pred_rel[0]
            c2_rel = pred_rel[1]
            self.create_relationship(c2_pred, concept_1, c2_rel, _commit=_commit)

    @read_txn
    def _get_all_terms(self):
        """Gets value, origin_name, and nanoid for all terms in database."""
        qry = (
            "MATCH (t:term) "
            "RETURN t.value AS term_val, t.origin_name AS term_origin, t.nanoid as term_nano"
        )
        return (qry, {})

    def get_term_synonyms(self, term: Term, threshhold: float = 0.8) -> List[dict]:
        """Returns list of dicts representing Term nodes synonymous to given Term"""
        if not (term.origin_name and term.value):
            logging.error("Term doesn't have origin_name and value")
            raise RuntimeError("arg 'term' must have both origin_name and value")
        # load spaCy NER model
        nlp = spacy.load("en_ner_bionlp13cg_md")
        # get result with all term values, origin_names, and nanoids in the database
        all_terms_result = self._get_all_terms()
        # get likely synonyms
        synonyms = []
        for record in all_terms_result:
            # calculate similarity between each Term and input Term
            term_1 = nlp(term.value)
            term_2 = nlp(str(record["term_val"]))  # type: ignore
            similarity_score = term_1.similarity(term_2)
            # if similarity threshold met, add to list of potential synonyms
            if similarity_score >= threshhold:
                synonym = {
                    "value": record["term_val"],  # type: ignore
                    "origin_name": record["term_origin"],  # type: ignore
                    "nanoid": record["term_nano"],  # type: ignore
                    "similarity": similarity_score,
                    "valid_synonym": 0,  # mark 1 if synonym when uploading later
                }
                synonyms.append(synonym)
        synonyms_sorted = sorted(synonyms, key=lambda d: d["similarity"], reverse=True)
        return synonyms_sorted

    def potential_synonyms_to_csv(
        self, input_data: List[dict], output_path: str
    ) -> None:
        """Given a list of synonymous Terms as dicts, outputs to CSV file at given output path"""
        with open(output_path, "w", encoding="utf8", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=input_data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(input_data)

    def link_term_synonyms_csv(self, term: Term, csv_path: str, _commit=None) -> None:
        """Given a CSV of syonymous Terms, links each via a Concept node to given Term"""
        with open(csv_path, encoding="UTF-8") as csvfile:
            synonym_reader = csv.reader(csvfile)
            for line in synonym_reader:
                if line[3] == "1":
                    synonym = Term()
                    synonym.value = line[0]
                    synonym.origin_name = line[1]
                    self.link_synonyms(term, synonym, _commit=_commit)

    @read_txn_data
    def get_property_synonyms(self, prop: Property):
        """
        Returns list of properties linked by concept to given property
        or to synonym of given property
        """
        if not prop.nanoid:
            logging.error("Property doesn't have a nanoid")
            raise RuntimeError("property entity needs a nanoid")
        p_attrs = self.get_entity_attrs(prop, output_str=False)
        prop_1 = N(label="property", props=p_attrs)
        prop_2 = N(label="property")
        vl_rel = VarLenR(Type="has_concept")
        trip = NoDirT(prop_1, vl_rel, prop_2)

        stmt = Statement(
            Match(trip),
            Return(f"distinct({prop_2.Return()})"),
            use_params=True
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms)
