# NAME

Bento::Meta::Model::Concept - object that models a semantic concept

# SYNOPSIS

# DESCRIPTION

# METHODS

- @terms = $concept->terms()

    Terms representing this concept (all of which are therefore
    synonymous, under the MDB).

- @entities = $concept->entities()

    Entities besides terms (nodes, edges, properties) that have (i.e.,
    express) this concept.

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
