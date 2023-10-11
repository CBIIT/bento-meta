"""
Script takes two MDF files representing different versions of the same
model and produces a Liquibase Changelog with the necessary changes to
an MDB in Neo4J to update the model from the old version to the new one.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import click
from bento_mdf.diff import diff_models
from bento_mdf.mdf import MDF
from bento_meta.entity import Entity
from bento_meta.objects import Concept, Edge, Node, Property, Tag, Term, ValueSet
from bento_meta.util.changelog import (
    changeset_id_generator,
    escape_quotes_in_attr,
    update_config_changeset_id,
)
from bento_meta.util.cypher.clauses import (
    Delete,
    DetachDelete,
    Match,
    Merge,
    Remove,
    Set,
    Statement,
)
from bento_meta.util.cypher.entities import G, N, P, R, T, _plain_var
from liquichange.changelog import Changelog, Changeset, CypherChange

logger = logging.getLogger(__name__)

ADD_NODE = "add property graph node"
REMOVE_NODE = "remove property graph node"
ADD_RELATIONSHIP = "add property graph relationship"
REMOVE_RELATIONSHIP = "remove property graph relationship"
ADD_PROPERTY = "add property graph property"
REMOVE_PROPERTY = "remove property graph property"


class DiffSplitter:
    """splits model diff into cypher statements that represent one change each"""

    def __init__(
        self, diff: Dict[str, Dict[str, Optional[Union[List, Dict]]]], model_handle: str
    ) -> None:
        self.diff = diff
        self.diff_summary = self.diff.pop("summary", None)
        self.model_handle = model_handle
        # entity_types order matters: earlier types may depend on later types
        # e.g. removing an edge whose src is a removed node
        self.entity_types = ["terms", "props", "edges", "nodes"]
        self.entity_classes: Dict[str, Type[Entity]] = {
            "nodes": Node,
            "edges": Edge,
            "props": Property,
            "terms": Term,
            "value_set": ValueSet,
            "concept": Concept,
            "tags": Tag,
        }
        self.diff_statements = []
        self.statement_order = [
            REMOVE_NODE,
            ADD_NODE,
            REMOVE_PROPERTY,
            ADD_PROPERTY,
            REMOVE_RELATIONSHIP,
            ADD_RELATIONSHIP,
        ]

    def get_diff_statements(self) -> List[Tuple[str, Union[Entity, dict]]]:
        """Split diff into segments & return sorted in segment_order"""
        for entity_type in self.entity_types:
            self.split_entity_diff(entity_type=entity_type)
        statements_sorted = sorted(
            self.diff_statements, key=lambda x: self.statement_order.index(x[0])
        )
        return [x[1] for x in statements_sorted]  # statement part only

    def add_node_statement(self, entity: Entity) -> None:
        """Add cypher statement that adds an entity"""
        escape_quotes_in_attr(entity)
        ent_c = N(label=entity.get_label(), props=entity.get_attr_dict())
        stmt = Statement(Merge(ent_c))
        self.diff_statements.append((ADD_NODE, stmt))

    def remove_node_statement(self, entity: Entity) -> None:
        """Add cypher statement that removes an entity"""
        escape_quotes_in_attr(entity)
        ent_c = N(label=entity.get_label(), props=entity.get_attr_dict())
        if isinstance(entity, Edge):
            src_c = N(label="node", props=entity.src.get_attr_dict())
            dst_c = N(label="node", props=entity.dst.get_attr_dict())
            src_trip = T(ent_c, R(Type="has_src"), src_c)
            dst_trip = T(ent_c, R(Type="has_dst"), dst_c)
            path = G(src_trip, dst_trip)
            match_clause = Match(path)
        else:
            match_clause = Match(ent_c)
        stmt = Statement(match_clause, DetachDelete(ent_c.var))

        self.diff_statements.append((REMOVE_NODE, stmt))

    def add_relationship_statement(self, src: Entity, rel: str, dst: Entity) -> None:
        """Add cypher statement that adds a relationship from src to dst entities"""
        for ent in [src, dst]:
            escape_quotes_in_attr(ent)
        rel_c = R(Type=rel)
        src_c = N(label=src.get_label(), props=src.get_attr_dict())
        dst_c = N(label=dst.get_label(), props=dst.get_attr_dict())
        plain_trip = T(_plain_var(src_c), rel_c, _plain_var(dst_c))
        stmt = Statement(Match(src_c, dst_c), Merge(plain_trip))

        self.diff_statements.append((ADD_RELATIONSHIP, stmt))

    def remove_relationship_statement(self, src: Entity, rel: str, dst: Entity) -> None:
        """Add cypher statement that removes a relationship from src to dst entities"""
        for ent in [src, dst]:
            escape_quotes_in_attr(ent)
        rel_c = R(Type=rel)
        src_c = N(label=src.get_label(), props=src.get_attr_dict())
        dst_c = N(label=dst.get_label(), props=dst.get_attr_dict())
        trip = T(src_c, rel_c, dst_c)
        stmt = Statement(Match(trip), Delete(_plain_var(rel_c)))

        self.diff_statements.append((REMOVE_RELATIONSHIP, stmt))

    def add_long_relationship_statement(
        self,
        parent: Entity,
        parent_rel: str,
        obj_ent: Entity,
        src: Entity,
        rel: str,
        dst: Entity,
    ) -> None:
        """
        Add cypher statement that adds a relationship from src to dst entities

        Includes (parent)-[parrel]-(obj) relationship to correctly match ent.
        """
        for ent in [parent, obj_ent, src, dst]:
            escape_quotes_in_attr(ent)
        parent_c = N(label=parent.get_label(), props=parent.get_attr_dict())
        parent_rel_c = R(Type=parent_rel)
        rel_c = R(Type=rel)
        src_c = N(label=src.get_label(), props=src.get_attr_dict())
        dst_c = N(label=dst.get_label(), props=dst.get_attr_dict())

        # kludge for concepts - need to clean up rel. direction stuff
        if obj_ent.get_label() == src_c.label:
            parent_trip = T(parent_c, parent_rel_c, src_c)
        else:
            parent_trip = T(parent_c, parent_rel_c, dst_c)

        plain_trip = T(_plain_var(src_c), rel_c, _plain_var(dst_c))
        stmt = Statement(Match(parent_trip, dst_c), Merge(plain_trip))

        self.diff_statements.append((ADD_RELATIONSHIP, stmt))

    def remove_long_relationship_statement(
        self,
        parent: Entity,
        parent_rel: str,
        obj_ent: Entity,
        src: Entity,
        rel: str,
        dst: Entity,
    ) -> None:
        """
        Add cypher statement that removes a relationship from src to dst entities

        Includes (parent)-[parrel]-(src) relationship to correctly id src ent.
        """
        for ent in [parent, obj_ent, src, dst]:
            escape_quotes_in_attr(ent)
        parent_c = N(label=parent.get_label(), props=parent.get_attr_dict())
        parent_rel_c = R(Type=parent_rel)
        rel_c = R(Type=rel)
        src_c = N(label=src.get_label(), props=src.get_attr_dict())
        dst_c = N(label=dst.get_label(), props=dst.get_attr_dict())

        # kludge for concepts - need to clean up rel. direction stuff
        if obj_ent.get_label() == src_c.label:
            parent_trip = T(parent_c, parent_rel_c, src_c)
        else:
            parent_trip = T(parent_c, parent_rel_c, dst_c)

        trip = T(src_c, rel_c, dst_c)
        stmt = Statement(Match(parent_trip, trip), Delete(_plain_var(rel_c)))

        self.diff_statements.append((REMOVE_RELATIONSHIP, stmt))

    def add_property_statement(
        self, entity: Entity, prop_handle: str, prop_value: Any
    ) -> None:
        """Add cypher statement that adds a property to an entity"""
        escape_quotes_in_attr(entity)
        prop_value_unesc = prop_value.replace(r"\'", "'").replace(r"\"", '"')
        prop_value_esc = prop_value_unesc.replace("'", r"\'").replace('"', r"\"")

        prop_c = P(handle=prop_handle, value=prop_value_esc)
        ent_c_noprop = N(label=entity.get_label(), props=entity.get_attr_dict())
        ent_c_prop = N(label=entity.get_label(), props=entity.get_attr_dict())
        ent_c_prop._add_props(prop_c)
        ent_c_prop.var = ent_c_noprop.var
        stmt = Statement(Match(ent_c_noprop), Set(ent_c_prop.props[prop_handle]))

        self.diff_statements.append((ADD_PROPERTY, stmt))

    def remove_property_statement(self, entity: Entity, prop_handle: str) -> None:
        """Add cypher statement that removes a property from an entity"""
        escape_quotes_in_attr(entity)
        ent_c = N(label=entity.get_label(), props=entity.get_attr_dict())
        stmt = Statement(Match(ent_c), Remove(ent_c, prop=prop_handle))

        self.diff_statements.append((REMOVE_PROPERTY, stmt))

    def update_simple_attr_segment(
        self, entity: Entity, attr: str, old_value: Any, new_value: Any
    ) -> None:
        """Add segment to update simple attribute."""
        if old_value and not new_value:
            self.remove_property_statement(
                entity=entity,
                prop_handle=attr,
            )
        else:
            self.add_property_statement(
                entity=entity,
                prop_handle=attr,
                prop_value=new_value,
            )

    def update_object_attr_segment(
        self,
        entity: Entity,
        attr: str,
        old_values: Dict[str, Entity],
        new_values: Dict[str, Entity],
    ) -> None:
        """
        Add segment to update object attribute.

        These are 'term containers' like concept & value_set.
        """
        object_attr_class = self.entity_classes.get(attr)
        if not object_attr_class:
            raise AttributeError(f"{attr} not in self.entity_classes")
        object_attr = object_attr_class()
        object_attr = self.get_entity_of_type(entity_type=attr)
        parent, parent_rel, obj_ent = self.get_triplet(
            entity=entity, attr=attr, value=object_attr
        )
        if new_values and not old_values:
            # add relationship between entity and object attr if DNE
            self.add_relationship_statement(src=parent, rel=parent_rel, dst=obj_ent)
        for old_value in old_values.values():
            old_entity = self.get_entity_of_type(
                entity_type="terms", entity_attr_dict=old_value.get_attr_dict()
            )
            src, rel, dst = self.get_triplet(
                entity=object_attr, attr="terms", value=old_entity
            )
            self.remove_long_relationship_statement(
                parent=parent,
                parent_rel=parent_rel,
                obj_ent=obj_ent,
                src=src,
                rel=rel,
                dst=dst,
            )
        for new_value in new_values.values():
            new_entity = self.get_entity_of_type(
                entity_type="terms", entity_attr_dict=new_value.get_attr_dict()
            )
            src, rel, dst = self.get_triplet(
                entity=object_attr, attr="terms", value=new_entity
            )
            self.add_long_relationship_statement(
                parent=parent,
                parent_rel=parent_rel,
                obj_ent=obj_ent,
                src=src,
                rel=rel,
                dst=dst,
            )

    def update_collection_attr_segment(
        self,
        entity: Entity,
        attr: str,
        old_values: Dict[str, Entity],
        new_values: Dict[str, Entity],
    ) -> None:
        """
        Update collection attr (e.g. list of props, tags, terms of an object attr)

        parent_entity is for Valuesets & Concepts so that it can locate the correct one.
        """
        for old_value in old_values.values():
            old_entity = self.get_entity_of_type(
                entity_type=attr, entity_attr_dict=old_value.get_attr_dict()
            )
            if isinstance(old_entity, Tag):  # not handled in add/rem
                self.remove_node_statement(entity=old_entity)
            src, rel, dst = self.get_triplet(entity=entity, attr=attr, value=old_entity)
            self.remove_relationship_statement(src=src, rel=rel, dst=dst)
        for new_value in new_values.values():
            new_entity = self.get_entity_of_type(
                entity_type=attr, entity_attr_dict=new_value.get_attr_dict()
            )
            if isinstance(new_entity, Tag):  # not handled in add/rem
                self.add_node_statement(entity=new_entity)
            src, rel, dst = self.get_triplet(entity=entity, attr=attr, value=new_entity)
            self.add_relationship_statement(src=src, rel=rel, dst=dst)

    def get_triplet(
        self, entity: Entity, attr: str, value: Entity
    ) -> Tuple[Entity, str, Entity]:
        """Uses mapspec() to get rel name and direction, returns src, rel, dst"""
        rel_str = entity.mapspec()["relationship"][attr]["rel"]
        rel = rel_str.replace(":", "").replace("<", "").replace(">", "")

        if ">" not in rel_str:  # True unless rel is from left to right
            return (value, rel, entity)
        return (entity, rel, value)

    def get_class_attrs(
        self, entity_type: Type[Entity], include_generic_attrs: bool = True
    ) -> Dict[str, List[str]]:
        """
        Get class attrs from entity class's attspec_, returns tuple of

        If include_generic_attrs=True, adds Entity.att_spec_ attrs without a '_' prefix.
        """
        class_attrs = entity_type.attspec_

        if include_generic_attrs:
            generic_atts = {x: y for x, y in Entity.attspec_.items() if x[0] != "_"}
            ent_attrs = {**generic_atts, **class_attrs}
        else:
            ent_attrs = class_attrs

        simple_attrs = [x for x, y in ent_attrs.items() if y == "simple"]
        obj_attrs = [x for x, y in ent_attrs.items() if y == "object"]
        coll_attrs = [x for x, y in ent_attrs.items() if y == "collection"]

        return {
            "simple": simple_attrs,
            "object": obj_attrs,
            "collection": coll_attrs,
        }

    def get_entity_of_type(
        self, entity_type: str, entity_attr_dict: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """returns instantiated entity of given type with given attrs"""
        object_attr_class = self.entity_classes.get(entity_type)
        if not object_attr_class:
            raise AttributeError(f"{entity_type} not in self.entity_classes")
        if entity_attr_dict:
            return object_attr_class(entity_attr_dict)
        return object_attr_class()

    def generate_entity_from_key(
        self,
        entity_type: str,
        entity_key: Union[str, Tuple[str, str], Tuple[str, str, str]],
    ) -> Entity:
        """Generate bento-meta entity from its key"""
        if entity_type == "nodes":
            return Node({"handle": entity_key, "model": self.model_handle})
        if entity_type == "edges" and len(entity_key) == 3:
            return Edge(
                {
                    "handle": entity_key[0],
                    "model": self.model_handle,
                    "src": Node({"handle": entity_key[1], "model": self.model_handle}),
                    "dst": Node({"handle": entity_key[2], "model": self.model_handle}),
                }
            )
        if entity_type == "props" and len(entity_key) == 2:
            return Property(
                {
                    "handle": entity_key[1],
                    "model": self.model_handle,
                    "_parent_handle": entity_key[0],
                }
            )
        if entity_type == "terms" and len(entity_key) == 2:
            return Term({"value": entity_key[0], "origin_name": entity_key[1]})
        raise ValueError(f"Unknown entity type: {entity_type}")

    def split_entity_diff(self, entity_type: str) -> None:
        """For each entity type in diff (e.g. nodes, edges, props), splits into segments"""
        entity_diff = self.diff.get(entity_type)
        if not entity_diff:
            logger.warning(f"No diff for entity type {entity_type}")
            return
        # removed entities
        removed_entities = entity_diff.get("removed", {})
        if removed_entities:
            for entity in removed_entities.values():
                self.remove_node_statement(entity=entity)
        # added entities
        added_entities = entity_diff.get("added", {})
        if added_entities:
            for entity in added_entities.values():
                self.add_node_statement(entity=entity)
                if entity_type == "edges":
                    self.add_relationship_statement(
                        src=entity, rel="has_src", dst=entity.src
                    )
                    self.add_relationship_statement(
                        src=entity, rel="has_dst", dst=entity.dst
                    )
        # changed entities (updated attrs)
        class_attrs = self.get_class_attrs(entity_type=self.entity_classes[entity_type])
        for entity_key, change_dict in entity_diff.get("changed", {}).items():
            entity = self.generate_entity_from_key(
                entity_type=entity_type, entity_key=entity_key
            )
            for attr, attr_changes in change_dict.items():
                # update simple attribute (e.g. desc/is_required)
                if attr in class_attrs["simple"]:
                    self.update_simple_attr_segment(
                        entity=entity,
                        attr=attr,
                        old_value=attr_changes.get("removed", []),
                        new_value=attr_changes.get("added", []),
                    )
                # update object attr (i.e. term container, e.g. concept, value_set)
                elif attr in class_attrs["object"]:
                    self.update_object_attr_segment(
                        entity=entity,
                        attr=attr,
                        old_values=attr_changes.get("removed", []),
                        new_values=attr_changes.get("added", []),
                    )
                # update collection attr (e.g. list of props, tags)
                elif attr in class_attrs["collection"]:
                    self.update_collection_attr_segment(
                        entity=entity,
                        attr=attr,
                        old_values=attr_changes.get("removed", []),
                        new_values=attr_changes.get("added", []),
                    )
                else:
                    raise AttributeError(
                        f"Attribute '{attr}' not found in {class_attrs} for {entity_type}"
                    )


def convert_diff_to_changelog(
    diff, model_handle: str, author: str, config_file_path: str
) -> Changelog:
    """converts diff beween two models to a changelog"""
    changeset_id = changeset_id_generator(config_file_path=config_file_path)
    changelog = Changelog()
    diff_splitter = DiffSplitter(diff, model_handle)
    diff_statements = diff_splitter.get_diff_statements()

    for cypher_statement in diff_statements:
        changelog.add_changeset(
            Changeset(
                id=str(next(changeset_id)),
                author=author,
                change_type=CypherChange(text=str(cypher_statement)),
            )
        )

    update_config_changeset_id(
        config_file_path=config_file_path, new_changeset_id=next(changeset_id)
    )

    return changelog


@click.command()
@click.option(
    "--model_handle",
    required=True,
    type=str,
    prompt=True,
    help="CRDC Model Handle (e.g. 'GDC')",
)
@click.option(
    "--old_mdf_files",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    multiple=True,
    help="Older version of MDF file(s)",
)
@click.option(
    "--new_mdf_files",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    multiple=True,
    help="Newer version of MDF file(s)",
)
@click.option(
    "--output_file_path",
    required=True,
    type=click.Path(),
    prompt=True,
    help="File path for output changelog",
)
@click.option(
    "--config_file_path",
    required=True,
    type=click.Path(exists=True),
    help="Changeset config file path",
)
@click.option(
    "--author",
    required=True,
    type=str,
    help="author for changeset. default=MDB_ADMIN",
)
@click.option(
    "--_commit",
    required=False,
    type=str,
    help="commit string",
)
def main(
    model_handle: str,
    old_mdf_files: Union[str, List[str]],
    new_mdf_files: Union[str, List[str]],
    output_file_path: str,
    config_file_path: str,
    author: str,
    _commit: Optional[str],
) -> None:
    """
    get liquibase changelog from different versions of mdf files for a model
    """
    mdf_old = MDF(*old_mdf_files, handle=model_handle, raiseError=True)
    mdf_new = MDF(*new_mdf_files, handle=model_handle, _commit=_commit, raiseError=True)
    if not mdf_old.model or not mdf_new.model:
        raise RuntimeError("Error getting model from MDF")

    model_old = mdf_old.model
    model_new = mdf_new.model

    diff = diff_models(mdl_a=model_old, mdl_b=model_new)
    changelog = convert_diff_to_changelog(
        diff=diff,
        model_handle=model_handle,
        author=author,
        config_file_path=config_file_path,
    )
    path = Path(output_file_path)
    changelog.save_to_file(file_path=str(path), encoding="UTF-8")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
