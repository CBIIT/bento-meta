"""
ToolsMDB: subclass of 'WriteableMDB' to support interactions with the MDB.

EntityValidator: validates that entities have required attributes.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from importlib.util import find_spec
from logging.config import fileConfig
from pathlib import Path
from subprocess import check_call
from sys import executable
from typing import TYPE_CHECKING, ClassVar

from minicypher.clauses import (
    As,
    Collect,
    DetachDelete,
    Match,
    Merge,
    OptionalMatch,
    Return,
    With,
)
from minicypher.entities import N0, R0, G, N, P, R, T, _plain_var
from minicypher.functions import count
from minicypher.statement import Statement

from bento_meta.entity import Entity
from bento_meta.mdb import make_nanoid, read_txn_data, read_txn_value
from bento_meta.mdb.writeable import WriteableMDB, write_txn
from bento_meta.objects import (
    Concept,
    Edge,
    Node,
    Predicate,
    Property,
    Tag,
    Term,
    ValueSet,
)

if TYPE_CHECKING:
    from neo4j import Record

# logging stuff
log_ini_path = Path(__file__).parents[2].joinpath("logs/log.ini")
log_file_path = Path(__file__).parents[2].joinpath(f"logs/{__name__}.log")
fileConfig(log_ini_path, defaults={"logfilename": log_file_path.as_posix()})
logger = logging.getLogger(__name__)


class ToolsMDB(WriteableMDB):
    """:class:`bento_meta.mdb.writeable.WriteableMDB` subclass with mdb-tools."""

    def __init__(self, uri: str | None, user: str | None, password: str | None) -> None:
        """Initialize a :class:`ToolsMDB` object."""
        super().__init__(uri=uri, user=user, password=password)

    class EntityNotUniqueError(Exception):
        """Entity's attributes identify more than 1 property graph node in an MDB."""

    class EntityNotFoundError(Exception):
        """Entity's attributes fail to identify a property graph node in an MDB."""

    class PatternNotUniqueError(Exception):
        """Match pattern's attributes identify more than 1 triple in an MDB."""

    class PatternNotFoundError(Exception):
        """Match pattern's attributes fail to identify a triple in an MDB."""

    @read_txn_value  # type: ignore[reportArgumentType]
    def _get_entity_count(self, entity: Entity) -> list[Record]:
        """
        Return count of given entity found in an MDB.

        - If count = 0, entity with given attributes not found in MDB.
        - If count = 1, entity with given attributes is unique in MDB.
        - If count > 1, more attributes needed to uniquely id entity in MDB.

        Args:
            entity: The entity to count.

        Returns:
            List with count value.
        """
        ent = N(label=entity.get_label(), props=entity.get_attr_dict())

        stmt = Statement(
            Match(ent),
            Return(count(ent)),
            As("entity_count"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "entity_count")  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def _get_pattern_count(self, pattern: T | G) -> list[Record]:
        """
        Return count of given match pattern (triple or path) found in an MDB.

        Property graph triple: (n)-[r]->(m)
        Path: set of overlapping triples

        - If count = 0, pattern with given attributes not found in MDB.
        - If count = 1, pattern with given attributes is unique in MDB.
        - If count > 1, more attributes needed to uniquely id pattern in MDB.

        Args:
            pattern: The pattern (triple or path) to count.

        Returns:
            List with count value.
        """
        stmt = Statement(
            Match(pattern),
            Return(count("*")),
            As("pattern_count"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "pattern_count")  # type: ignore[reportReturnType]

    def validate_entity_unique(self, entity: Entity) -> None:
        """
        Validate that the given entity occurs once (& only once) in an MDB.

        Note: doesn't validate the entity itself because not all entity attributes
        are necessarily required to locate an entity in the MDB.
        (e.g. handle and model OR nanoid alone can identify a node)

        Args:
            entity: The entity to validate.

        Raises:
            EntityNotUniqueError: If entity attributes match multiple property
                graph nodes in the MDB.
            EntityNotFoundError: If entity attributes don't match any in the MDB.
        """
        ent_count = int(self._get_entity_count(entity)[0])
        if ent_count > 1:
            logger.error(str(self.EntityNotUniqueError))
            raise self.EntityNotUniqueError
        if ent_count < 1:
            logger.error(str(self.EntityNotFoundError))
            raise self.EntityNotFoundError

    def validate_entities_unique(self, entities: Iterable[Entity]) -> None:
        """Run self.validate_entity_unique() over multiple entities."""
        for entity in entities:
            self.validate_entity_unique(entity)

    def validate_pattern_unique(self, pattern: T | G) -> None:
        """
        Validate that the given match pattern occurs once (& only once) in an MDB.

        Args:
            pattern: The pattern to validate.

        Raises:
            PatternNotUniqueError: If pattern attributes match multiple triples
                in the MDB.
            PatternNotFoundError: If pattern attributes don't match any in the MDB.
        """
        pattern_count = int(self._get_pattern_count(pattern)[0])
        if pattern_count > 1:
            logger.error(
                str(
                    self.PatternNotUniqueError(
                        f"Pattern: {pattern.pattern()} not unique.",
                    ),
                ),
            )
            msg = f"Pattern: {pattern.pattern()} not unique."
            raise self.PatternNotUniqueError(msg)
        if pattern_count < 1:
            logger.error(
                str(
                    self.PatternNotFoundError(
                        f"Pattern: {pattern.pattern()} not found.",
                    ),
                ),
            )
            msg = f"Pattern: {pattern.pattern()} not found."
            raise self.PatternNotFoundError(msg)

    @write_txn  # type: ignore[reportArgumentType]
    def remove_entity_from_mdb(self, entity: Entity) -> list[Record]:
        """
        Remove given Entity node from the database.

        Accepts the following bento-meta Entities:
            Concept, Node, Predicate, Property, Edge, Term

        Args:
            entity: The entity to remove.

        Returns:
            List of Records from the transaction.
        """
        self.validate_entity_unique(entity)

        ent_label = entity.get_label()
        ent_attrs = entity.get_attr_dict()

        ent = N(label=ent_label, props=ent_attrs)

        stmt = Statement(Match(ent), DetachDelete(ent._var), use_params=True)

        qry = str(stmt)
        parms = stmt.params

        logger.info("Removing %s entity with with properties: %s", ent_label, ent_attrs)
        return (qry, parms)  # type: ignore[reportReturnType]

    @write_txn  # type: ignore[reportArgumentType]
    def add_entity_to_mdb(
        self,
        entity: Entity,
        _commit: str | None = None,
    ) -> list[Record]:
        """
        Add given Entity node to MDB instance.

        Args:
            entity: The entity to add.
            _commit: Optional commit string to tag the entity.

        Returns:
            List of Records from the transaction.
        """
        EntityValidator.validate_entity(entity)
        EntityValidator.validate_entity_has_attribute(entity, "nanoid")

        if _commit:
            entity._commit = _commit

        ent_label = entity.get_label()
        ent_attrs = entity.get_attr_dict()

        ent = N(label=ent_label, props=ent_attrs)  # type: ignore[arg-type]

        if isinstance(entity, Edge):
            src = N(label="node", props=entity.src.get_attr_dict())
            dst = N(label="node", props=entity.dst.get_attr_dict())
            src_rel = R(Type="has_src")
            dst_rel = R(Type="has_dst")
            src_trip = src_rel.relate(_plain_var(ent), _plain_var(src))
            dst_trip = dst_rel.relate(_plain_var(ent), _plain_var(dst))
            stmt = Statement(
                Merge(ent),
                Merge(src),
                Merge(dst),
                Merge(src_trip),
                Merge(dst_trip),
                use_params=True,
            )
        else:
            stmt = Statement(Merge(ent), use_params=True)

        qry = str(stmt)
        parms = stmt.params

        logger.info(
            "Merging new %s node with properties: %s into the MDB",
            ent_label,
            ent_attrs,
        )

        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_concept_nanoids_linked_to_entity(
        self,
        entity: Entity,
        mapping_source: str | None = None,
    ) -> list[Record]:
        """
        Return list of concept nanoids linked to given entity.

        The concept(s) have "represents" or "has_concept" relationships tagged with
        the given mapping source. If no mapping source is provided, return all.

        Args:
            entity: The entity to get concepts for.
            mapping_source: Optional mapping source to filter by.

        Returns:
            List of concept nanoids.
        """
        self.validate_entity_unique(entity)

        ent = N(label=entity.get_label(), props=entity.get_attr_dict())
        concept = N(label="concept")
        if isinstance(entity, Term):
            rel = R(Type="represents")
        else:
            rel = R(Type="has_concept")
        ent_trip = rel.relate(ent, concept)

        if mapping_source is not None:
            tag = N(
                label="tag",
                props={"key": "mapping_source", "value": mapping_source},
            )
            tag_trip = T(concept, R(Type="has_tag"), tag)
            path = G(ent_trip, tag_trip)
        else:
            path = ent_trip

        stmt = Statement(
            Match(path),
            Return(f"{concept._var}.nanoid"),
            As("concept_nanoids"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params
        logger.debug("%s; %s", qry, parms)

        return (qry, parms, "concept_nanoids")  # type: ignore[reportReturnType]

    @write_txn  # type: ignore[reportArgumentType]
    def add_relationship_to_mdb(
        self,
        relationship_type: str,
        src_entity: Entity,
        dst_entity: Entity,
        _commit: str = "",
    ) -> list[Record]:
        """
        Add relationship between given entities in MDB.

        Args:
            relationship_type: The type of relationship to create.
            src_entity: Source entity for the relationship.
            dst_entity: Destination entity for the relationship.
            _commit: Optional commit string to tag the relationship.

        Returns:
            List of Records from the transaction.
        """
        self.validate_entities_unique([src_entity, dst_entity])

        rel = R(Type=relationship_type)

        src = N(label=src_entity.get_label(), props=src_entity.get_attr_dict())
        dst = N(label=dst_entity.get_label(), props=dst_entity.get_attr_dict())
        trip = rel.relate(src, dst)
        plain_trip = rel.relate(_plain_var(src), _plain_var(dst))

        try:
            # check for existance shouldn't include _commit?
            self.validate_pattern_unique(trip)
        except self.PatternNotFoundError:
            # if triple doesn't already exist, add _commit? this means that
            # if triple exists w/ different _commit, merge shouldn't add anything?
            rel.props["_commit"] = P(handle="_commit", value=_commit)

        stmt = Statement(Match(src, dst), Merge(plain_trip), use_params=True)

        qry = str(stmt)
        parms = stmt.params

        logger.info(stmt)

        logger.info(
            "Adding %s relationship between src %s with properties: %s to dst %s "
            "with properties: %s",
            relationship_type,
            src.label,
            src_entity.get_attr_dict(),
            dst.label,
            dst_entity.get_attr_dict(),
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    def link_synonyms(
        self,
        entity_1: Entity,
        entity_2: Entity,
        mapping_source: str,
        _commit: str = "",
    ) -> None:
        """
        Link two synonymous entities in the MDB via a Concept node.

        Takes two synonymous Entities (as determined by user/SME) as bento-meta
        objects and connects them to a Concept node via a 'represents' relationship.

        Entities must both exist in the MDB instance and given entity attributes must
        uniquely identify property graph nodes in the MDB.

        Args:
            entity_1: First entity to link.
            entity_2: Second entity to link.
            mapping_source: Source of the mapping relationship.
            _commit: Optional commit string. If set, the _commit property of any node
                created is set to this value.
        """
        self.validate_entities_unique([entity_1, entity_2])

        ent_1_concepts = self.get_concept_nanoids_linked_to_entity(
            entity=entity_1,
            mapping_source=mapping_source,
        )
        ent_2_concepts = self.get_concept_nanoids_linked_to_entity(
            entity=entity_2,
            mapping_source=mapping_source,
        )
        shared_concepts = list(set(ent_1_concepts).intersection(ent_2_concepts))

        # has concept been tagged by this mapping src before
        if shared_concepts:
            logger.warning(
                "This mapping has already been added by this source via "
                "Concept with nanoid: %s",
                shared_concepts[0],
            )
            return

        # one of the entities has a concept created by the given mapping source
        if ent_1_concepts:
            logger.info("Using existing concept with nanoid %s", ent_1_concepts[0])
            concept = Concept({"nanoid": ent_1_concepts[0]})
        elif ent_2_concepts:
            logger.info("Using existing concept with nanoid %s", ent_2_concepts[0])
            concept = Concept({"nanoid": ent_2_concepts[0]})
        else:
            concept = Concept({"nanoid": make_nanoid()})
            self.add_entity_to_mdb(concept, _commit=_commit)
            self.add_tag_to_mdb_entity(
                tag=Tag(
                    {
                        "key": "mapping_source",
                        "value": mapping_source,
                        "nanoid": make_nanoid(),
                    }
                ),
                entity=concept,
            )

        # create specified relationship between each entity and a concept
        rel_type_1 = "represents" if isinstance(entity_1, Term) else "has_concept"
        rel_type_2 = "represents" if isinstance(entity_2, Term) else "has_concept"

        self.add_relationship_to_mdb(
            relationship_type=rel_type_1,
            src_entity=entity_1,
            dst_entity=concept,
            _commit=_commit,
        )
        self.add_relationship_to_mdb(
            relationship_type=rel_type_2,
            src_entity=entity_2,
            dst_entity=concept,
            _commit=_commit,
        )

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_entity_nanoid(self, entity: Entity) -> list[Record]:
        """Take a unique entity in the MDB and return its nanoid."""
        self.validate_entity_unique(entity)

        ent = N(label=entity.get_label(), props=entity.get_attr_dict())

        if isinstance(entity, Edge):
            src = N(label="node", props=entity.src.get_attr_dict())
            dst = N(label="node", props=entity.dst.get_attr_dict())
            src_rel = R(Type="has_src")
            dst_rel = R(Type="has_dst")
            src_trip = src_rel.relate(ent, src)
            dst_trip = dst_rel.relate(ent, dst)
            path = G(src_trip, dst_trip)
            match_clause = Match(path)
        else:
            match_clause = Match(ent)

        stmt = Statement(
            match_clause,
            Return(f"{ent._var}.nanoid"),
            As("entity_nanoid"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "entity_nanoid")  # type: ignore[reportReturnType]

    def get_or_make_entity_nanoid(self, entity: Entity) -> str:
        """Obtain existing entity's nanoid or create one for new entity."""
        try:
            return self.get_entity_nanoid(entity)[0]
        except self.EntityNotFoundError:
            return make_nanoid()

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_term_nanoids(
        self,
        concept: Concept,
        mapping_source: str = "",
    ) -> list[Record]:
        """Return list of term nanoids representing given concept."""
        self.validate_entity_unique(concept)

        ent = N(label="concept", props=concept.get_attr_dict())
        term = N(label="term")
        ent_trip = T(term, R(Type="represents"), ent)

        if mapping_source:
            tag_trip = T(
                concept,
                R(Type="has_tag"),
                N(
                    label="tag",
                    props={"key": "mapping_source", "value": mapping_source},
                ),
            )
            path = G(ent_trip, tag_trip)
        else:
            path = ent_trip

        stmt = Statement(
            Match(path),
            Return(f"{term._var}.nanoid"),
            As("term_nanoids"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "term_nanoids")  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_predicate_nanoids(
        self,
        concept: Concept,
        mapping_source: str = "",
    ) -> list[Record]:
        """Return list of predicate nanoids with relationship to given concept."""
        self.validate_entity_unique(concept)

        ent = N(label="concept", props=concept.get_attr_dict())
        predicate = N(label="predicate")
        ent_trip = T(predicate, R0(), ent)

        if mapping_source:
            tag = N(
                label="tag",
                props={"key": "mapping_source", "value": mapping_source},
            )
            tag_trip = T(ent, R(Type="has_tag"), tag)
            path = G(ent_trip, tag_trip)
        else:
            path = ent_trip

        stmt = Statement(
            Match(path),
            Return(f"{predicate._var}.nanoid"),
            As("predicate_nanoids"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "predicate_nanoids")  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_relationship_between_entities(
        self,
        src_entity: Entity,
        dst_entity: Entity,
    ) -> list[Record]:
        """
        Return relationship type between given entities.

        Relationship pattern: (src)-[:rel_type]->(dst).
        """
        self.validate_entities_unique([src_entity, dst_entity])

        trip = T(
            N(label=src_entity.get_label(), props=src_entity.get_attr_dict()),
            R(),
            N(label=dst_entity.get_label(), props=dst_entity.get_attr_dict()),
        )

        stmt = Statement(
            Match(trip),
            Return(f"TYPE({trip._edge._var})"),
            As("relationship_type"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms, "relationship_type")  # type: ignore[reportReturnType]

    def link_concepts_via_predicate(
        self,
        subject_concept: Concept,
        object_concept: Concept,
        predicate: Predicate,
        _commit: str = "",
    ) -> None:
        """
        Link two synonymous Concepts via a Predicate.

        This function takes two synonymous Concepts as bento-meta objects and links
        them via a Predicate node and has_subject and has_object relationships.

        Args:
            subject_concept: The subject concept.
            object_concept: The object concept.
            predicate: The predicate linking them.
            _commit: Optional commit string to tag created nodes.
        """
        self.validate_entities_unique([subject_concept, object_concept, predicate])

        predicate.subject = subject_concept
        predicate.object = object_concept

        predicate.nanoid = self.get_or_make_entity_nanoid(predicate)
        self.add_entity_to_mdb(predicate, _commit=_commit)

        self.add_relationship_to_mdb(
            relationship_type="has_subject",
            src_entity=predicate,
            dst_entity=predicate.subject,
            _commit=_commit,
        )
        self.add_relationship_to_mdb(
            relationship_type="has_object",
            src_entity=predicate,
            dst_entity=predicate.object,
            _commit=_commit,
        )

    def merge_two_concepts(
        self,
        concept_1: Concept,
        concept_2: Concept,
        mapping_source: str = "",
        _commit: str = "",
    ) -> None:
        """
        Combine two synonymous Concepts into a single Concept.

        This function takes two synonymous Concepts as bento-meta objects and
        merges them into a single Concept along with any connected Terms and Predicates.

        Args:
            concept_1: First concept (will remain after merge).
            concept_2: Second concept (will be deleted after merge).
            mapping_source: Source of the mapping relationship.
            _commit: Optional commit string to tag relationships.
        """
        self.validate_entities_unique([concept_1, concept_2])

        # get list of terms connected to concept 2
        c2_term_nanoids = self.get_term_nanoids(concept_2, mapping_source)
        c2_terms: list[Term] = [Term({"nanoid": nanoid}) for nanoid in c2_term_nanoids]

        # get list of predicates connected to concept 2
        c2_predicate_nanoids = self.get_predicate_nanoids(concept_2, mapping_source)
        c2_predicates_with_rel = []
        for nanoid in c2_predicate_nanoids:
            predicate = Predicate({"nanoid": nanoid})
            predicate_rel = self.get_relationship_between_entities(
                src_entity=predicate,
                dst_entity=concept_2,
            )[0]
            c2_predicates_with_rel.append((predicate, predicate_rel))

        # delete concept 2
        self.remove_entity_from_mdb(concept_2)

        # connect terms from deleted (c2) to remaining concept (c1)
        for term in c2_terms:
            self.add_relationship_to_mdb(
                relationship_type="represents",
                src_entity=term,
                dst_entity=concept_1,
                _commit=_commit,
            )

        # connect predicates from deleted (c2) to remaining concept (c1)
        for predicate, rel in c2_predicates_with_rel:
            self.add_relationship_to_mdb(
                relationship_type=rel,
                src_entity=predicate,
                dst_entity=concept_1,
                _commit=_commit,
            )

    @read_txn_data  # type: ignore[reportArgumentType]
    def _get_all_terms(self) -> list[Record]:
        """Return list of all terms in an MDB."""
        term = N(label="term")

        stmt = Statement(Match(term), Return(term._var))

        qry = str(stmt)
        parms = {}

        logger.debug(qry)

        return (qry, parms)  # type: ignore[reportReturnType]

    def get_potential_term_synonyms(
        self,
        term: Term,
        threshhold: float = 0.8,
    ) -> list[dict]:
        """
        Return list of dicts representing potential synonymous Term nodes.

        Args:
            term: The term to find synonyms for.
            threshhold: Similarity threshold (0-1) for considering terms synonymous.

        Returns:
            List of dicts with value, origin_name, nanoid, similarity, valid_synonym.
        """
        self.validate_entity_unique(term)

        nlp = _get_nlp_model()

        all_terms_result = self._get_all_terms()
        all_terms = [list(item.values())[0] for item in all_terms_result]

        # get likely synonyms
        synonyms = []
        for term_attr_dict in all_terms:
            # calculate similarity between each Term and input Term
            term_1 = nlp(term.value)
            term_2 = nlp(term_attr_dict["value"])
            similarity_score = term_1.similarity(term_2)
            # if similarity threshold met, add to list of potential synonyms
            if similarity_score >= threshhold:
                synonym = {
                    "value": term_attr_dict["value"],
                    "origin_name": term_attr_dict["origin_name"],
                    "nanoid": term_attr_dict["nanoid"],
                    "similarity": similarity_score,
                    "valid_synonym": 0,  # mark 1 if synonym when uploading later
                }
                synonyms.append(synonym)
        return sorted(synonyms, key=lambda d: d["similarity"], reverse=True)

    def potential_synonyms_to_csv(
        self,
        input_data: list[dict],
        output_path: str,
    ) -> None:
        """
        Write CSV with list of synonymous Terms as dicts to given output path.

        Args:
            input_data: List of dicts representing potential synonyms.
            output_path: Path to write CSV file to.
        """
        with Path(output_path).open("w", encoding="utf8", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=input_data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(input_data)

    def link_term_synonyms_csv(
        self,
        term: Term,
        csv_path: str,
        mapping_source: str,
        _commit: str = "",
    ) -> None:
        """
        Link Terms in a CSV of synonymous Terms to given Term via a Concept node.

        Args:
            term: The term to link synonyms to.
            csv_path: Path to CSV file containing potential synonyms.
            mapping_source: Source of the mapping relationship.
            _commit: Optional commit string to tag relationships.
        """
        with Path(csv_path).open(encoding="UTF-8") as csvfile:
            synonym_reader = csv.reader(csvfile)
            for line in synonym_reader:
                if line[3] == "1":  # valid_synonym
                    synonym = Term({"value": line[0], "origin_name": line[1]})
                    self.link_synonyms(
                        entity_1=term,
                        entity_2=synonym,
                        mapping_source=mapping_source,
                        _commit=_commit,
                    )

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_property_synonyms_direct(
        self,
        entity: Property,
        mapping_source: str = "",
    ) -> list[Record]:
        """
        Return list of properties linked by concept to given property.

        Args:
            entity: The property to get synonyms for.
            mapping_source: Optional mapping source to filter by.

        Returns:
            List of Records with property synonyms.
        """
        self.validate_entity_unique(entity)

        ent = N(label="property", props=entity.get_attr_dict())
        prop = N(label="property")
        concept = N(label="concept")
        ent_trip_1 = T(ent, R(Type="has_concept"), concept)
        ent_trip_2 = T(prop, R(Type="has_concept"), concept)

        if mapping_source:
            tag = N(
                label="tag",
                props={"key": "mapping_source", "value": mapping_source},
            )
            tag_trip = T(concept, R(Type="has_tag"), tag)
            path = G(ent_trip_1, ent_trip_2, tag_trip)
        else:
            path = G(ent_trip_1, ent_trip_2)

        stmt = Statement(
            Match(path),
            With(f"{Collect(_plain_var(prop).pattern())}"),
            As("synonyms"),
            Return("synonyms"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms)  # type: ignore[reportReturnType]

    def _get_property_synonyms_direct_as_list(self, entity: Property) -> list[Property]:
        """
        Convert results of read_txn_data-wrapped function with one Property to a list.

        Args:
            entity: The property to get synonyms for.

        Returns:
            List of bento_meta.objects.Property entities.
        """
        data = self.get_property_synonyms_direct(entity)
        return [Property(s) for s in data[0]["synonyms"]]

    def get_property_synonyms_all(self, entity: Property) -> list[Property]:
        """
        Return list of properties linked by concept to given property or its synonyms.

        Chains through synonyms of given property (and so on).

        Args:
            entity: The property to get all synonyms for.

        Returns:
            List of Property entities that are synonyms.
        """
        self.validate_entity_unique(entity)
        all_synonyms = []
        queue = [entity]
        visited = {entity.nanoid}

        while queue:
            current = queue.pop(0)
            direct_synonyms = self._get_property_synonyms_direct_as_list(current)
            for synonym in direct_synonyms:
                if synonym.nanoid not in visited:
                    visited.add(synonym.nanoid)
                    queue.append(synonym)
                    all_synonyms.append(synonym)

        return all_synonyms

    @read_txn_data  # type: ignore[reportArgumentType]
    def _get_property_parents_data(self, entity: Property) -> list[Record]:
        """
        Get list of nodes/edges connected to given property.

        Parents are Nodes or Edges via the "has_property" relationship.

        Args:
            entity: The property to get parents for.

        Returns:
            List of Records with nodes and edges.
        """
        self.validate_entity_unique(entity)
        p_attrs = entity.get_attr_dict()
        child_prop = N(label="property", props=p_attrs)
        parent_node = N(label="node")
        parent_edge = N(label="relationship")
        rel = R(Type="has_property", _dir="_left")
        trip1 = rel.relate(child_prop, N0())
        trip2 = rel.relate(_plain_var(child_prop), parent_node)
        trip3 = rel.relate(_plain_var(child_prop), parent_edge)

        stmt = Statement(
            Match(trip1),
            OptionalMatch(trip2),
            OptionalMatch(trip3),
            With(),
            Collect(_plain_var(parent_node).pattern()),
            As("nodes,"),
            Collect(_plain_var(parent_edge).pattern()),
            As("edges"),
            Return("nodes, edges"),
            use_params=True,
        )

        qry = str(stmt)
        parms = stmt.params

        return (qry, parms)  # type: ignore[reportReturnType]

    def get_property_parents(self, entity: Property) -> list[Node | Edge]:
        """
        Get parents of a property as a list of bento_meta Nodes or Edges.

        Args:
            entity: The property to get parents for.

        Returns:
            List of Node or Edge entities.
        """
        self.validate_entity_unique(entity)

        data = self._get_property_parents_data(entity)
        node_parents = [Node(p) for p in data[0]["nodes"]]
        edge_parents = [Edge(p) for p in data[0]["edges"]]
        return node_parents + edge_parents

    def add_tag_to_mdb_entity(self, tag: Tag, entity: Entity) -> None:
        """
        Add a tag to an existing entity in an MDB.

        Args:
            tag: The tag to add.
            entity: The entity to tag.
        """
        self.validate_entity_unique(entity)
        self.add_entity_to_mdb(tag)
        self.add_relationship_to_mdb(
            relationship_type="has_tag",
            src_entity=entity,
            dst_entity=tag,
        )


class EntityValidator:
    """Class to validate that bento-meta entities have all required attributes."""

    required_attrs_by_entity_type: ClassVar[dict[type[Entity], list[str]]] = {
        Node: ["handle", "model"],
        Edge: ["handle", "model", "src", "dst"],
        Property: ["handle", "model"],
        Term: ["origin_name", "value"],  # add? "origin_id", "origin_version"
        Concept: ["nanoid"],
        Predicate: ["handle", "subject", "object"],
        Tag: ["key", "value"],
        ValueSet: ["handle"],
    }

    valid_attrs: ClassVar[dict[tuple[type[Entity], str], set[str]]] = {
        (Predicate, "handle"): {
            "exactMatch",
            "closeMatch",
            "broader",
            "narrower",
            "related",
        }
    }

    class MissingAttributeError(Exception):
        """An entity doesn't have the attributes required for unique identification."""

    class InvalidAttributeError(Exception):
        """An entity attribute is invalid."""

    @staticmethod
    def validate_entity_has_attribute(entity: Entity, attr_name: str) -> None:
        """Validate the presence of an entity's attribute."""
        if not getattr(entity, attr_name):
            msg = f"{entity.__class__.__name__} needs a {attr_name} attribute"
            raise EntityValidator.MissingAttributeError(msg)

    @staticmethod
    def _validate_entity_attribute(entity_type: type[Entity], attr_name: str) -> None:
        """Check that an entity attribute is in a set of valid attributes."""
        valid_attrs = EntityValidator.valid_attrs.get((entity_type, attr_name))

        if valid_attrs and getattr(entity_type, attr_name) not in valid_attrs:
            msg = (
                f"{entity_type.__name__} {attr_name} must be one of: "
                f"{', '.join(list(valid_attrs))}"
            )
            raise EntityValidator.InvalidAttributeError(msg)

    @staticmethod
    def validate_entity(entity: Entity) -> None:
        """
        Check if entity has all attributes required by MDB for its type.

        Also checks validates all of those attributes are valid themselves if they
        are entities or if they have a fixed set of possible values.

        If looking for a unique identifier for the entity (i.e. nanoid), ensures
        entity has all the required attributes for unique identification.

        Args:
            entity: The entity to validate.

        Raises:
            ValueError: If entity type not supported.
            MissingAttributeError: If required attribute missing.
            InvalidAttributeError: If attribute value invalid.
        """
        entity_type = type(entity)
        required_attrs = EntityValidator.required_attrs_by_entity_type.get(entity_type)

        if not required_attrs:
            msg = f"Entity type {entity_type.__name__} not supported"
            raise ValueError(msg)

        try:
            for attr_name in required_attrs:
                # validate attr that is an entity (e.g. Edge.src)
                if isinstance(getattr(entity, attr_name), Entity):
                    EntityValidator.validate_entity(getattr(entity, attr_name))
                # check entity has attr if required
                EntityValidator.validate_entity_has_attribute(entity, attr_name)
                # check attr with fixed set of possible values is valid
                EntityValidator._validate_entity_attribute(entity_type, attr_name)
        except (
            EntityValidator.MissingAttributeError,
            EntityValidator.InvalidAttributeError,
        ):
            logger.exception("Error validating entity")
            raise


def _get_nlp_model():
    """Install and import spacy & scispacy nlp model if any not already installed."""
    model_name = "en_ner_bionlp13cg_md"
    model_url = "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_ner_bionlp13cg_md-0.5.1.tar.gz"

    try:
        if not find_spec("spacy"):  # ensure spacy is installed
            check_call([executable, "-m", "pip", "install", "spacy"])
        import spacy

        if not find_spec(model_name):  # ensure model is installed
            check_call([executable, "-m", "pip", "install", model_url])
        nlp = spacy.load(model_url)
        return nlp
    except Exception:
        logger.exception("Error getting NLP model")
        raise
