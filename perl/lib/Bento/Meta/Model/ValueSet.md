# NAME

Bento::Meta::Model::ValueSet - object that models an enumerated set of property values

# SYNOPSIS

# DESCRIPTION

# METHODS

- id(), set\_id($id\_string)
- url(), set\_id($url)

    Informative URL ideally pointing to a description of the set of values.

- terms(), set\_terms( $term\_value => $term\_obj)

    The terms aggregated by the value set.

- prop()

    The property (object) whose value set this is.

- origin, set\_origin($origin\_obj)

    Origin object represnting the source authority of the term set, if any.

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
