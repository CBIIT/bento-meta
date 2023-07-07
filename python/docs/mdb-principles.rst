Metamodel Database (MDB) Principles
===================================

MDB Motivation and Rationale
____________________________

The MDB schema is intended to be simple in structure, without a profusion of different classes for specialized entities. At the same time, enough entities are provided to enable a separation between an entity and its semantic meaning as represented in the MDB.
The goals are:

* To be able to store multiple models, developed independently for specific practical uses, to exist separately in a single data store. and also
  
* To be able to relate aspects of these independent models to semantic standards, and so encourage reuse of models, model substructures, and vocabulary.

To the extent the MDB succeeds in meeting these goals, it also yields useful mappings of terminology and structures between models. This feature is intended to facilitate data transformations that contribute to interoperability between projects or programs that might participate in an MDB. 

A key aspect of the MDB, one that distinguishes it from systems that serve similar purposes, is that it is meant to be responsive and dynamic -- easily and perhaps frequently changed and updated. An MDB requires curation and quality management, but it is not devised to be a standard reference or a database of record. Its value is increased by incorporating stable entities from external such references (e.g., the `NCIt <https://ncit.nci.nih.gov/ncitbrowser/>`_), but it is designed as a tool to assist data SMEs who are managing new or rapidly changing data resources, characterized by frequent data augmentation, addition of new data sources, or modification of data models or structures, often based on scientific considerations or policy decisions.

MDB Design Decisions
____________________

This milieu in which the MDB operates leads to the following design decisions and usage conventions:

- *Creating, updating, and reading information from the MDB must be easy and intuitive for data management subject matter experts (SME).*

Software to perform these functions must support the SME users in this regard. For example, an SME needs robust and straightforward tools to manipulate the MDB that make the underlying database structure and conventions transparent. The SME should be able to change or update what is necessary in the database, without worrying about whether she will "break it" by doing so.

- *It is more important that the MDB describes the current data models (and so the current data) in the ecosystem accurately, than it is that the MDB is "complete" in other respects.*

The MDB is a tool for managing active data. It can and should be anchored by elements of standards, and should by virtue of its capacity as a management tool reflect changes to those standards. However, the goal is not to incorporate a complete rendition of any standard, but to track the current modeling of current data in the managed ecosystem.

Practically, this may mean that semantic annotation of model lags behind the development *and use* of the model themselves. A value set of acceptable terms as recorded in an MDB may not immediately cover the entire value set defined by an external standard, yet the MDB is still useful for data validation in this state, and can be quickly updated to include valid terms as gaps are encountered.

- *The MDB is intentionally designed to capture logical data models easily. Conceptual data models and abstract metamodels can indeed be captured and annotated, but this is secondary to the main use case of the MDB.*

In our (FNLCR/BACS/CTOS) systems, the logical data model as captured in the MDB is very close to the physical representation of the data in our underlying native graph databases. This is intentional, in that it enables our databases to be directly configured by data SMEs, with little work necessary from engineering. However, the graph model underlying the MDB is a flexible abstraction that can capture the structure of RDBMS schemas, document-based data stores, UML representations, and other such artifacts.

- *The MDB can represent semantic information and relationships among concepts, such as synonymy of terms. These features are designed primarily to facilitate pragmatic mapping between models from constituent systems that need to interoperate.*

Semantic relationships as stored in the MDB, while meant to be reasonable and may be based on external standard ontologies or other conventions, are intended to be dynamic and solve practical interoperability problems, rather than abide strictly by any given standard or ruleset.

For example, the meanings of Patient and Participant as English words are distinct, and one may be used in the vernacular of a clinical trial, the other in a survey of healthy individuals.  In the `NCIt <https://ncit.nci.nih.gov/ncitbrowser/>`_ the former is concept C16960, and the latter (Study Participant) is C142710 -- i.e, the terms are not synonymous in the context of this authority. However, if the task is to relate entities between a clinical trial dataset and a dataset derived from healthy individuals, in order to aggregate or compare the underlying data, then the two terms should be considered as practical synonyms, in the sense that the individuals in both studies have analogous purposes in the study designs.

An MDB may capture this pragmatic synonymy to support the task of aligning and aggregating data, without representing an subject matter opinion or implying any universal statement about the two concepts.

MDB Entities and Structures
___________________________

A basic working principle is that a data model of almost any type can be rendered usefully as a `graph <https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph>`_, containing

.. _nodes_relationships_properties:
* *Nodes* - logical data groupings
* *Relationships* - logical or structural links or references between nodes, and
* *Properties* - Variables, columns, or slots for actual data items.

A data model may be concieved of directly in this form, or translated from a different form. For example, in an `RDBMS <https://en.wikipedia.org/wiki/Relational_database>`_ schema, tables can map to nodes, columns to properties, and foreign key references to relationships. 

Other means of describing a data model may do so with more detail, or be more complete in some other sense. For example, in a `UML representation <https://en.wikipedia.org/wiki/Unified_Modeling_Language>`_, a specific model entity (say, a "clinical data form") may derive from a more general entity (say, a "form"), and may inherit certain variables or other attributes from the general entity (say, a form field such as "Patient ID"). This kind of class inheritance is *not* part of the MDB specification, although it could be emulated within MDB conventions. This is an example of how an MDB model intentionally tends to reflect how the data itself will be stored.

Data items are very frequently codes or strings chosen from a closed set of acceptable or valid values. In the MDB, the entity that represents a single such value is the Term. 

.. _terms:
* *Terms* - entities which include a string representation (value) for a specific datum, and information on its source origin or authority.

Term entities may also include semantic information such as definitions and external identifiers that link back to their authoritative origin. For example, a Term adopted from the NCI Thesaurus would have an origin_id attribute set to its NCIt Concept Code.

Terms are associated with their Origin, but not directly with any Model. This is an intentional design decision that allows a model to build value sets by reusing terms from different sources, via the Value Set entity.

.. _value_sets:
* *Value Sets* - entities which aggregate Terms and so represent controlled vocabularies or acceptable value lists for Property values.

When Term entities are used to describe an acceptable value for a Property, they do so via a grouping entity called a Value Set. A given Term can be a part of any Value Set for any Model via the addition of a graph edge. Properties that accept data from a controlled vocabulary are linked to a Value Set entity, and Term entities that represent the acceptable values link to the Value Set. See :ref:`this figure <term_valueset_pattern>`.

Terms have an additional role in the MDB, to annotate Concept entities with semantic information. 

.. _concepts:
* *Concepts* - entities which represent any abstract intellectual concept; a Concept's meaning is "induced" by Term entities that are linked to it via a "represents" graph edge.

The Concept entity is essentially a Term aggregation node, similar in function to a Value Set entity. It is an abstraction that enables the meanings of entities (not just Terms, but also Node, Relationships, and Properties) to be present in the database, and allows different models to reuse conceptual constructs and meanings defined by external authorities and elsewhere.

For example, a model may have a Node (logical data grouping) called "diagnosis". Other models may have a similar Node, which may or may not have the same Properties (data slots), but with the same logic behind the data grouping. In such a case, it could be helpful to document that similarity of purpose in the MDB, for cross-model mapping or analysis. The Concept node is intended to provide that capability.
In this example, Nodes from different models that group infomation bearing on diagnosis would all have an edge (``has_concept``) directed to a single Concept node.

The Concept node itself, as a database entity, does not describe the concept. Instead, the semantic meaning of a Concept is imputed by the Terms that are linked to the Concept. The Terms are said to "represent" the Concept.

Continuing with the example:  "Diagnosis" is an intellectual concept that is defined, among other places, at the NCI Thesaurus, where its concept code is C15220. In the formalism of the MDB, a Term entity, containing the ``value`` "Diagnosis", the ``origin_name`` "NCIt", and the ``origin_code`` C15220, would link to the Concept through a ``represents`` graph edge.

One might rather simply put that information directly into the Concept node --  this is not disallowed. However, by using the Concept-Term indirection, one can also very simply add other Terms that describe synonyous concepts coming from other external authorities. Another Term, with ``value`` ``SDTM-MHEDTTYP`` and ``origin_name`` CDISC, could be created and linked to the Concept node. This single *addition* to the MDB graph then captures the idea that the two notions of diagnosis are synonymous. Further, models that agree with each other with respect to NCIt could be translated into `CDISC <https://www.cdisc.org/>`_ representations with straightforward graph database queries. Because this update adds to the graph and does not change its previous structure, existing queries or interpretations that rely on the MDB are not affected.

Although the MDB is not primarily a knowledge base, it may be useful to record additional semantic information, especially for situations in which the mappings between model entities are not precisely synonymous, but reflect another kind of relationship. Mapping model entities to the `BRIDG <https://bridgmodel.nci.nih.gov/>`_ conceptual model, for example, is often characterized by a number of semantic "steps" beyond synonymy. For this purpose, the MDB defines a Predicate entity.

.. _predicates:
* *Predicates* - entities which represent a semantic relationship between two concepts, the "subject" and the "object".

A Predicate entity enables the formation of "triples" among Concept entities in the MDB. For example, the "generative" or "parent-child" relationship mentioned above can be represented by a Predicate entity linking parent and child concepts. 

The Predicate is also abstract entity, which can be linked to its own Concept entity, annotated by a Term. In practice, this fully general structure may not be required, especially if the entity it is meant to be used to facilitate mapping and not to be visible per se to the end users of an implementation. For example, a Predicate to indicate a hierarchical relationship may simply have a handle ``broader`` or ``is_a`` and an additional attribute indicating a formal source (`skos:broader <https://www.w3.org/TR/skos-reference/#broader>`_).

Models and Meanings
___________________

A helpful way to think of an MDB is to consider it as a layering of three views or functions on a data model:

* Structure: consisting of Models, Nodes, Relationships, and Properties;

* Vocabulary or Terminology: consisting of Origins, Value Sets, and Terms;

* Semantics: consisting of Concepts and Predicates.

While the indirection built into the MDB schema adds complexity, it also enables any of these three representations to be added to and updated independently of the others. This is key to the principle that data models should be managed dynamically. For example, it has allowed the team to develop model structure for a project and share it with stakeholders very rapidly (in a matter of days), without having to make decisions about vocabulary (acceptable value lists) right away.

However, this approach requires an SME to make some intellectual distinctions that may not seem intuitive. Almost every MDB entity has a ``handle`` property, rather than a ``name``. This is exactly because SMEs tend to associate "names" with terminology. In the MDB, the ``handle`` should very definitely be a human-readable word that describes the entity in its subject matter context; otherwise SMEs, engineers, and others could not talk about it usefully. But the ``handle`` is not a Term: it is a string that is also meant to conform to a standard that can be used by software downstream. Handles could be described as "local" or "internal" vocabulary that have a conventional meaning within the team. 

A Term, on the other hand, is more than its string representation. First, that representation is intentionally called its ``value`` (*not* "handle"), since that representation is meant to indicate precisely what incoming data itself would contain. In addition, a Term entity can additional information that points it to an external authority or Origin, where its semantic content is kept. A Term may have an external id or a human-readable definition. These Term attributes are explicitly known as ``origin_id`` and ``origin_definition`` to remind a user that the MDB is not (necessarily) the semantic authority.

So with handles and Terms, we can create a Node which is meant to represent a collection of data corresponding to, e.g., a clinical diagnosis. The ``handle`` of this Node would naturally be ``clinical_diagnosis``, which is human-readable and human-discussable, but conforms with the MDB spec to make it computable downstream. If it is important in the project to also associate that Node with an external defined terminology, a Term entity needs to be created to contain that information. The Term could reference the NCIt concept C15607 (the ``origin_id``)  and have a value "Clinical Diagnosis", which is the NCIt label for this concept.

In the MDB, the way to connect the Term with the Node (or other) entity is indirect. It might be natural to simply link the Term directly to the Node. It is more flexible, and easier to change the connections between evolving models and evolving vocabularies, to consider that Model entities and associated Terms reflect an _interaction_ between two independent structure, the pragmatic project model, and an external standard. That interaction is captured in the Concept entity. To relate the Term "Clinical Diagnosis" and the Node ``clinical_diagnosis`` in the MDB, we create an (anonymous) Concept instance, and create links to say that the Node "has_concept" Concept, and the Term "represent" that same Concept.

This seems cumbersome, and it may be, but with appropriate APIs to the database, an SME or engineer will not need to think about it. One benefit of the approach, however, is that one can query the MDB for semantic mapping completely independently of any models stored there. All Terms that attach (via ``represent``) to a given Concept entity are considered to be synoymous, in the working context of the MDB. New models with semantically identical Nodes can be mapped into existing terminology (and therefore, existing mappings and translations) by a single association of the new model's entities to the correct Concept entities. This is a curation step that can be performed separately from creating the model structure itself. 

If there is a distinction of meaning between two nodes with a similar structural role in two models (say "veterinary diagnosis" and "clinical diagnosis"), this can also be handled by addition to the MDB, without structurally changing it. In this case, creating a new Concept entity to attach to a Node ``veterinary_diagnosis``, and linking that Concept to the "Clinical Diagnosis" Concept with a Predicate ``is_related_to``, may suffice for the practical purposes of mapping between models. If a Term (again, an external stable semantic entity) that represents the idea of "veterinary diagnosis" is found, that can be added to the new Concept in the MDB later.
