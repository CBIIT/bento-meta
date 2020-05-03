# NAME

Bento::Meta::MDF - Create model objects from model description files

# SYNOPSIS

    $model = Bento::Meta::MDF->create_model(@mdf_files);
    # $model isa Bento::Meta::Model

# DESCRIPTION

[Bento::Meta::MDF](/lib/Bento/Meta/MDF.md) defines a [Bento::Meta::Model](/lib/Bento/Meta/Model.md) factory, `create_model()`,
that accepts model description files as specified at [bento-mdf](https://github.com/CBIIT/bento-mdf).

In particular, it follows the merging protocol describes at
[https://github.com/CBIIT/bento-mdf#multiple-input-yaml-files-and-overlays](https://github.com/CBIIT/bento-mdf#multiple-input-yaml-files-and-overlays).

# METHOD

- create\_model(@mdf\_yaml\_files)

    Returns a [Bento::Meta::Model](/lib/Bento/Meta/Model.md) object.

# AUTHOR

    Mark A. Jensen <mark -dot- jensen -at- nih -dot- gov>
    FNL
