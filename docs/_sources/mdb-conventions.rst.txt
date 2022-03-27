MDB Maintenance Principles and Conventions
==========================================

Conventions and software tools based on the following principles and
guidelines are necessary to enable maintenance of an MDB. The
organization of data of the MDB instance needs to be stable and
predictable so that data does not get lost, incorrectly duplicated,
or mutated.

As the data grows, and especially as the interconnections
between different models and mappings into common vocabularies
increase, the database will become less and less amenable to manual
updates via Cypher statements or one-off scripts. At the same time, as the
complexity grows, so does the utility and value of the MDB, as long as
it remains consistent -- so that queries always return what the schema
says they will return.

To maintain this kind of consistency, but also treat the MDB as a
dynamic store of information that is amenable to frequent change,
robust software tools for updating the database are necessary. These
tools alleviate the need for SMEs and engineers to remember the schema
and prevent shortcuts that would affect the outcome of standard
queries that are based on the expectations set by the schema.

This principle does *not* say that *additional* nodes, properties, or
relationships cannot ever be added to an MDB. Reasons of performance
tuning, tagging, indexing, setting "placeholders" or "cursors", are
all valid enhancements or temporary modifications. If such
enhancements make sense to add to the general MDB schema, then they
should be so added. The key question to ask before making permanent
enhancements should be: *Will they break existing queries?* If so,
then discussion, deprecation and update planning is necessary.

Temporary structural additions to the database to facilitate
maintenance or fixes may be appropriate. It is critical to plan ahead,
so that the database admin can back completely out of such modifications after
they have performed their function.

MDB entity properties required for consistency
______________________________________________

The MDB schema is flexible, but the following properties and entities
are critical for its functionality.

All entities need to posses a non-null *nanoid*. This is a six
character, alphanumeric random identifier, which can be generated with
the ``nanoid`` package in various languages (e.g., `for python <https://github.com/puyuan/py-nanoid>`_. Once set for an entity in an MDB
instance, it should not be changed, even when other properties are
updated, added, or removed. The nanoid (plus a version string,
possibly) should uniquely identify all single Neo4j nodes in the
database instance.

An important reason for maintaining the nanoid on an entity through
changes (and also to retire a nanoid if an entity is removed) is that
it serves as a handle or short-cut for the Simple Terminology
Service (`STS <https://github.com/CBIIT/bento-sts>`_. Appending a nanoid to the STS /id endpoint must always return that
entity as a JSON document. Versions of an entity are allowed, but a
version string should qualify the original nanoid for retrieval; new
versions of an existing entity should not receive a new nanoid.

Node, Relationship, and Property entities must all possess a non-null ``model``
property, set to the model the entity is describing. For each unique
value of the ``model`` property, a corresponding Model entity (Neo4j
node) should exist, that describes the model further. A Neo4j
relationship between model entities and the corresponding Model node
are not necessary or expected under the schema.

Value Set and Term entities are intentionally _not_ associated
directly with any model - this enables the idea of reuse of the same
terms across different models. However, every Term must have an
_origin_ property that indicates an authoritative source for the term
and its meaning. 

Value Sets may have an origin property, if the set itself is a product
of an external authority. An example would be the value domain for
ethnicity according to the caDSR, with public id 2016566, consisting
of five terms.

MDB indexes needed for additional functionality
_______________________________________________

For integration with the STS, and for performance, the Neo4j instance
of an MDB requires certain indexes to be established. These are
specified in `these Cypher statements <githubref>`_. The primary
requirement is that fulltext, Lucene-based indexes should be created
on entity ``description`` and Term ``origin_definition`` properties to
enable "search box" like queries over the the entire graph. Regular
btree indexes on entity ``handle`` and Term ``value`` properties are also
highly recommended for fast query responses.

Conventions for consistent and idempotent updates
_________________________________________________


Models
^^^^^^

Data models under our management are generally maintained as `MDF <https://github.com/CBIIT/bento-mdf>`_ files
in open GitHub repositories. Data SMEs are able to make changes and
updates to models as necessary, and GitHub tracks and remembers all
changes. Branches created for development are extremely useful and
enable SMEs to work productively with engineers on upcoming features
while the latest production model remains accessible for users and the
production data system. 

Tapping into this existing work process is a natural place to
incorporate systematic updates to the MDB. Once model changes are
approved for production, the MDF can be made part of a GitHub
release. CI/CD processes (e.g., GitHub Actions or Jenkins) can
automatically pull new MDF releases and update the MDB with changes.

For this process to be deterministic, conventions must be established
that unambiguously define when differences between the MDF model and the
corresponding MDB model represents intended updates, and when they
indicate an error in the MDF. To do this, the intention of the SME
must be made clear in the data (i.e., the model description file)
itself. There also should be a way to back out of at least one update
if necessary.

Terms
^^^^^

*WIP*


















