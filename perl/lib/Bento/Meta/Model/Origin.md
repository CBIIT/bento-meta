# NAME

Bento::Meta::Model::Origin - object that models a term's authoritative source

# SYNOPSIS

# DESCRIPTION

# METHODS

- name(), set\_name($origin\_name)
- url(), set\_url($url)

    Ideally, the official URL for the authority or source.

- is\_external, set\_is\_external($bool)

    Source is external to the orginization running the MDB.

- @entities = $origin->entities()

    Terms or value sets which have this origin, source or authority.

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
