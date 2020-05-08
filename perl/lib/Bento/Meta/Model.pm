package Bento::Meta::Model;
use base Bento::Meta::Model::Entity;
use v5.10;
use Scalar::Util qw/blessed/;
use lib '../../../lib';
use Bento::Meta::Model::Node;
use Bento::Meta::Model::Edge;
use Bento::Meta::Model::Property;
use Bento::Meta::Model::ValueSet;
use Bento::Meta::Model::Origin;
use Bento::Meta::Model::Concept;
use Bento::Meta::Model::Term;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use Carp qw/croak/;
use Log::Log4perl qw/:easy/;
use strict;

# new($handle)
sub new {
  my $class = shift;
  my ($handle, $bolt_cxn) = @_;
  unless ($handle) {
    LOGDIE "Model::new() requires handle as arg1";
  }
  DEBUG "Creating Model object with handle '$handle'";
  my $self = $class->SUPER::new({
    _handle => $handle,
    _nodes => {},
    _edges => {},
    _props => {},
    _edge_table => {},
  });
  if ($bolt_cxn) { # create object maps
    unless (ref($bolt_cxn) eq 'Neo4j::Bolt::Cxn') {
      LOGDIE ref($self)."::new : arg2 must be a Neo4j::Bolt::Cxn";
    }
    $self->{_bolt_cxn} = $bolt_cxn;
    $self->_build_maps;
    $self->get;
  }
  return $self;
}

sub set_bolt_cxn {
  my $self = shift;
  my ($cxn) = @_;
  unless ( $cxn->isa('Neo4j::Bolt::Cxn') ) {
    LOGDIE ref($self)."::set_bolt_cxn : arg1 must be a Neo4j::Bolt::Cxn";
  }
  $self->_build_maps;
  $self->{_bolt_cxn} = $cxn;
}

sub bolt_cxn { shift->{_bolt_cxn} }

sub _build_maps {
  my $self = shift;
  for (qw/ Node Edge Property ValueSet Origin Concept Term /) {
    my $cls = "Bento::Meta::Model::$_";
    INFO "create $cls object map";
    $cls->object_map($cls->map_defn, $self->bolt_cxn);
  }
  return 1;
}

# retrieve named model from db
# get all the nodes, relationships and properties
sub get {
  my $self = shift;
  my ($refresh) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::get : Can't get model; no database connection set";
    return;
  }
  my $qry = cypher->match('n')
    ->where( { 'n.model' => $self->handle } )
    ->return('n');
  my $rows = $self->bolt_cxn->run_query($qry);
  return _fail_query($rows) if ($rows->failure);
  my (@n,@e,@p);
  while ( my ($n) = $rows->fetch_next ) {
    for ($n->{labels}) {
      grep(/^node$/,@$_) && do {
        my $a = Bento::Meta::Model::Node->new($n);
        $a->set_dirty(0);
        push @n, $a;
        last;
      };
      grep(/^relationship$/,@$_) && do {
        my $a = Bento::Meta::Model::Edge->new($n);
        $a->set_dirty(0);
        push @e, $a;
        last;
      };
      grep(/^property$/,@$_) && do {
        my $a = Bento::Meta::Model::Property->new($n);
        $a->set_dirty(0);
        push @p, $a;
        last;
      };
      LOGWARN ref($self)."::get : unhandled node type of ".join('/',@$_);
    }
  }
  unless (@n) {
    LOGWARN ref($self)."::get : no nodes returned for model '".$self->handle."'";
  }
  # now get() each node, which should load the object properties and
  # create the cache...
  $_->get($refresh) for (@n,@e,@p);
  ($self->{_nodes}{$_->handle} = $_) for @n;
  for (@e) {
    $self->{_edges}{$_->triplet} = $_;
    my ($t,$s,$d) = split /[:]/,$_->triplet;
    $self->{_edge_table}{$t}{$s}{$d} = $_;
  }
  for (@p) {
    for my $e ($_->entities) {
      my $pfx = (ref($e) =~ /Node$/ ? $e->handle :
                 $e->triplet);
      $self->{_props}{join(':',$pfx,$_->handle)} = $_;
    }
  }
  
  return $self;
}

# put - update the db model using the object model

sub put {
  my $self = shift;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::put : Can't get model; no database connection set";
    return;
  }
  # put() every dirty==1 object, belonging to the model, in the cache
  # for every unmapped object contained in the model, put it and all of its
  # unmapped/dirty descendants
  # but there can be cycles, so keep track of objects already visited and
  # short circuit in that case

  my $do;
  my %seen;
  $do = sub {
    my $obj = shift;
    return if $seen{"$obj"};
    $seen{"$obj"}++;
    $obj->put() if $obj->dirty == 1;
    for my $att (map { $_->[0] || () }
                   @{$obj->map_defn->{object}},
                 @{$obj->map_defn->{collection}}) {
      for my $ent ($obj->$att) {
        next unless defined $ent;
        $do->($ent);
      }
    }
    return;
  };

  for my $e ($self->removed_entities) {
     $do->($e);
  }
  for my $e ($self->edges) {
    $do->($e);
  }
  for my $n ($self->nodes) {
    $do->($n);
  }
  for my $p ($self->props) {
    $do->($p);
  }
  
  return 1;
}



sub _fail_query {
  my ($stream) = @_;
  my @c = caller(1);
  if ($stream->server_errmsg) {
    LOGWARN $c[3]." : server error: ".$stream->server_errmsg;
  }
  elsif ($stream->client_errmsg) {
    LOGWARN $c[3]."::get : client error: ".$stream->client_errmsg;
  }
  else {
    LOGWARN $c[3]."::get : unknown database-related error";
  }
  return
}

# create/delete API

# add_node( {handle =>'newnode', ...} ) or add_node($node)
# new node will be added to the Model nodes hash
sub add_node {
  my $self = shift;
  my ($init) = shift;
  if (ref($init) =~ /^HASH|Neo4j::Bolt::Node$/) {
    $init = Bento::Meta::Model::Node->new($init);
  }
  unless ($init->handle) {
    LOGDIE ref($self)."::add_node - init hash reqs 'handle' key/value";
  }
  if (defined $self->node($init->handle)) {
    LOGWARN ref($self)."::add_node : overwriting existing node with handle '".$init->handle."'";
  }
  $init->set_model($self->handle) if (!$init->model);
  if ($init->model ne $self->handle) {
    LOGWARN ref($self)."::add_node : model handle is '".$self->handle."', but node.model is '".$init->model."'";
  }
  for my $p ($init->props) { # add any props on this node to the model list
    $p->set_entities($init->handle => $init);
    $p->set_model($self->handle);
    $self->set_props(join(':',$init->handle,$p->handle) => $p);
  }
  $self->set_nodes($init->handle, $init);
}

# add_edge( { handle => 'newreln', src => $from_node, dst => $to_node, ... })
# or add_edge( $edge )
# note: the Edge obj created will always have src and dst attribs that
# are Node objects, and that appear in the Model node hash
# if node or node handle does not appear in Node,it will be added (with add_node)

sub add_edge {
  my $self = shift;
  my ($init) = shift;
  my $etbl = $self->{_edge_table};
  if (ref($init) =~ /^HASH|Neo4j::Bolt::Node$/) {
    $init = Bento::Meta::Model::Edge->new($init);
  }
  unless ( $init->handle && $init->src && $init->dst ) {
    LOGDIE ref($self)."::add_edge - init hash reqs 'handle','src','dst' key/values";
  }
  $init->set_model($self->handle) if (!$init->model);
  my ($hdl,$src,$dst) = split /:/,$init->triplet;
  if ($etbl->{$hdl} && $etbl->{$hdl}{$src} &&
        $etbl->{$hdl}{$src}{$dst}) {
    LOGWARN ref($self)."::add_edge : overwriting existing edge with handle/src/dest '".join("/",$hdl,$src,$dst)."'";
  }
  unless ($self->contains($init->src)) {
    LOGWARN ref($self)."::add_edge : source node '".$src."' is not yet in model, adding it";
    $self->add_node($init->src);
  }
  unless ($self->contains($init->dst)) {
    LOGWARN ref($self)."::add_edge : destination node '".$dst."' is not yet in model, adding it";
    $self->add_node($init->dst);
  }
  $etbl->{$hdl}{$src}{$dst} = $init;
  for my $p ($init->props) { # add any props on this edge to the model list
    $p->set_entities($init->triplet => $init);
    $p->set_model($self->handle);
    $self->set_props(join(':',$init->triplet,$p->handle) => $p);
  }
  $self->set_edges( $init->triplet => $init );
}

# add_prop( $node | $edge, {handle => 'newprop',...})
# new Property obj will be recorded in the Model props hash
# Prop object will be added to Node object existing in the Model nodes hash
# if node or edge does not appear in Node list, it will be added (with add_node
# or add_edge)
# require node or edge objects to exist - 

sub add_prop {
  my $self = shift;
  my ($ent, $init) = @_;
  unless ( ref($ent) =~ /Node|Edge$/ ) {
    LOGDIE ref($self)."::add_prop - arg1 must be Node or Edge object";
  }
  unless (defined $init) {
    LOGDIE ref($self)."::add_prop - arg2 must be init hash or Property object";
  }
  unless ($self->contains($ent)) {
    my ($thing) = ref($ent) =~ /::([^:]+)$/;
    $thing = lc $thing;
    my $thing_method = "add_$thing";
    LOGWARN ref($self)."::add_prop : $thing '".$ent->handle."' is not yet in model, adding it";
    $self->$thing_method($ent);
  }
  if (ref($init) eq 'HASH') {
    $init = Bento::Meta::Model::Property->new($init);
  }
  unless ($init->handle) {
    LOGDIE ref($self)."::add_prop - init hash (arg2) reqs 'handle' key/value";
  }
  $init->set_model($self->handle) if (!$init->model);
  my $pfx = $ent->can('triplet') ? $ent->triplet : $ent->handle;
  $init->set_entities($pfx => $ent); # "whom do I belong to?"
  if ( $self->prop(join(':',$pfx,$init->handle)) ) {
    LOGWARN ref($self)."::add_prop - overwriting existing prop '".join(':',$pfx,$init->handle)."'";
  }
  $ent->set_props( $init->handle => $init );
  $self->set_props( join(':',$pfx,$init->handle) => $init );
}

# add_terms($property, @terms_or_strings)
# $property - Property object
# @terms_or_strings - Terms objects or strings representing acceptable values
# warn and return if property doesn't have value_domain eq 'value_set'
# attach Terms to the property's ValueSet obj
# create a ValueSet objects if one doesn't exist
# create Term objects for plain strings
# returns the ValueSet object

sub add_terms {
  my $self = shift;
  my ($prop, @terms) = @_;
  unless (ref($prop) =~ /Property$/) {
    LOGDIE ref($self)."::add_terms : arg1 must be Property object";
  }
  unless (@terms) {
    LOGDIE ref($self)."::add_terms : arg2,... required (strings and/or Term objects";
  }
  $prop->value_domain // $prop->set_value_domain('value_set');
  unless ($prop->value_domain =~ /^value_set|enum$/) {
    LOGWARN ref($self)."::add_terms : property '".$prop->handle."' has value domain '".$prop->value_domain."', not 'value_set' or 'enum'";
    return;
  }
  my %terms;
  for (@terms) {
    if (ref =~ /Term$/) {
      $terms{$_->value} = $_;
      next;
    }
    elsif (!ref) {
      $terms{$_} = Bento::Meta::Model::Term->new({value => $_});
    }
    else {
      LOGDIE ref($self)."::add_terms : arg2,... must be strings or Term objects";
    }
  }
  my $vs = $prop->value_set;
  unless ($vs) {
    $vs = Bento::Meta::Model::ValueSet->new();
    $vs->set_id( $vs->make_uuid );
    $vs->set_prop($prop);
    $vs->set_handle( $self->handle.substr($vs->id,0,7) );
    $prop->set_value_set($vs)
  }
  $vs->set_terms($_ => $terms{$_}) for keys %terms;
  return $vs;
}

# rm_node( $node_or_handle )
# node must participate in no edges to be able to be removed (like neo4j)
# - so must rm_edge() first.
# returns the node removed
# removes the node's properties from the model list, but not
# from the node itself
sub rm_node {
  my $self = shift;
  my ($node) = @_;
  unless (ref($node) =~ /Node$/) {
    LOGDIE ref($self)."::rm_node - arg1 must be Node object";
  }
  if (!$self->contains($node)) {
    LOGWARN ref($self)."::rm_node : node '".$node->handle."' not contained in model '".$self->handle."'";
    return;
  }
  if ( $self->edges_by_src($node) ||
         $self->edge_by_dst($node) ) {
    LOGWARN ref($self)."::rm_node : can't remove node '".$node->handle."', it is participating in edges";
    return;
  }
  # remove node properties from the model list
  for my $p ($node->props) {
    # note, this only removes from the model list --
    # the prop list for the node itself is not affected
    # (i.e., the props remain attached to the deleted node)
    $self->set_props(join(':',$node->handle,$p->handle) => undef);
    # old $prop now in removed_entities
  }
  return $self->set_nodes( $node->handle => undef );
  # old $node now in removed_entities
}

# rm_edge( $edge_or_sth_else )
# returns the edge removed from the model list
# removes the edge's properties from the model list, but not
# from the edge itself
sub rm_edge {
  my $self = shift;
  my ($edge) = @_;
  unless (ref($edge) =~ /Edge$/) {
    LOGDIE ref($self)."::rm_edge - arg1 must be Edge object";
  }
  if (!$self->contains($edge)) {
    LOGWARN ref($self)."::rm_edge : edge '".$edge->triplet."' not contained in model '".$self->handle."'";
    return;
  }
  # remove node properties from the model list
  for my $p ($edge->props) {
    # note, this only removes props from the model list --
    # the prop list for the edge itself is not affected
    # (i.e., the props remain attached to the deleted edge)
    $self->set_props(join(':',$edge->triplet,$p->handle) => undef);
    # old $p now in removed_entities
  }
  my ($hdl,$src,$dst) = split /:/, $edge->triplet;
  delete $self->{_edge_table}{$hdl}{$src}{$dst};
  $edge->set_src(undef);
  $edge->set_dst(undef);
  return $self->set_edges( $edge->triplet => undef );
  # old $edge now in removed_entities
}

# rm_prop( $prop_or_handle )
# removes the property from the entity (node, edge) that has it,
# and from the model property list
# returns the prop removed
sub rm_prop {
  my $self = shift;
  my ($prop) = @_;
  unless (ref($prop) =~ /Property$/) {
    LOGDIE ref($self)."::rm_prop - arg1 must be Property object";
  }
  if (!$self->contains($prop)) {
    LOGWARN ref($self)."::rm_prop : property '".$prop->handle."' not contained in model '".$self->handle."'";
    return;
  }
  for my $e ($prop->entities) {
    if (ref($e) =~ /Edge$/) { # an edge prop
      $e->set_props( $prop->handle => undef );
      $self->prop( join(':',$e->triplet,$prop->handle) => undef );
      # old $prop now in removed_entities

    }
    elsif (ref($e) =~ /Node$/) { # a node prop
      $e->set_props( $prop->handle => undef );
      $self->prop( join(':',$e->handle,$prop->handle) => undef );
      # old $prop now in removed_entities
    }
  }
  return $prop; 
}

sub rm_terms {
  LOGDIE "not implemented";
}

# contains($entity) - true if entity object appears in model
sub contains {
  my $self = shift;
  my ($ent) = @_;
  unless ( blessed($ent) && $ent->isa('Bento::Meta::Model::Entity') ) {
    LOGWARN ref($self)."::contains - arg not an Entity object";
    return;
  }
  for (ref $ent) {
    /Node$/ && do {
      return !! grep { $_ == $ent } $self->nodes;
      last;
    };
    /Edge$/ && do {
      return !! grep { $_ == $ent } $self->edges;      
      last;
    };
    /Property$/ && do {
      return !! grep { $_ == $ent } $self->props;      
      last;
    };
    /ValueSet$/ && do {
      last;
    };
    /Term$/ && do {
      last;
    };
    /Concept$/ && do {
      last;
    };
  }
  return;
}

# read API

sub edges_in {
  my $self = shift;
  my ($node) = @_;
  unless (ref($node) =~ /Node$/) {
    LOGDIE ref($self)."::rm_node - arg1 must be Node object";
  }
  $self->edges_by_dst($node);
}

sub edges_out {
  my $self = shift;
  my ($node) = @_;
  unless (ref($node) =~ /Node$/) {
    LOGDIE ref($self)."::rm_node - arg1 must be Node object";
  }
  $self->edges_by_src($node);
}  

sub node { $_[0]->{_nodes}{$_[1]} }

# this overrides Entity::nodes
sub nodes { return $_[0]->node($_[1]) if @_ > 1; values %{shift->{_nodes}} }

sub prop { $_[0]->{_props}{$_[1]} }

# this overrides Entity::props
sub props { return $_[0]->prop($_[1]) if @_ > 1; values %{shift->{_props}} }

# this overrides Entity::edges
sub edges { return $_[0]->edge($_[1]) if @_ > 1; values %{shift->{_edges}} }
sub edge {
  my $self = shift;
  my ($type,$src,$dst) = @_;
  if ($type =~ /:/) { # triplet
    ($type,$src,$dst) = split /:/,$type;
  }
  else {
    $type = $type->name if ref $type;
    $src = $src->name if ref $src;
    $dst = $dst->name if ref $dst;
  }
  return $self->{_edge_table}{$type}{$src}{$dst};
}

sub edge_by_src { shift->edges_by_src(@_) }
sub edge_by_dst { shift->edges_by_dst(@_) }
sub edge_by_type { shift->edges_by_type(@_) }

sub edges_by_src { shift->edge_by('src',@_) }
sub edges_by_dst { shift->edge_by('dst',@_) }
sub edges_by_type { shift->edge_by('type',@_) }

sub edge_by {
  my $self = shift;
  my ($key, $arg) = @_;
  unless ($key =~ /^src|dst|type$/) {
    LOGDIE ref($self)."::edge_by : arg 1 must be one of src|dst|type";
  }
  if (ref($arg) =~ /Model/) {
    $arg = $arg->handle;
  }
  elsif (ref $arg) {
    LOGDIE ref($self)."::edge_by : arg must be a ".__PACKAGE__."-related object or string, not ".ref($arg);
  }
  my @ret;
  for ($key) {
    /^src$/ && do {
      for my $t (keys %{$self->{_edge_table}}) {
        for my $u (keys %{$self->{_edge_table}{$t}{$arg}}) {
          push @ret, $self->{_edge_table}{$t}{$arg}{$u} // ();
        }
      }
      last;
    };
    /^dst$/ && do {
      for my $t (keys %{$self->{_edge_table}}) {
        for my $u (keys %{$self->{_edge_table}{$t}}) {
          push @ret, $self->{_edge_table}{$t}{$u}{$arg} // ();
        }
      }
      last;
    };
    /^type$/ && do {
      for my $t (keys %{$self->{_edge_table}{$arg}}) {
        for my $u (keys %{$self->{_edge_table}{$arg}{$t}}) {
          push @ret, $self->{_edge_table}{$arg}{$t}{$u} // ();
        }
      }
      last;
    };
  }
  return @ret;
}
1;

=head1 NAME

Bento::Meta::Model - object bindings for Bento Metamodel Database

=head1 SYNOPSIS

 # empty model with name $handle:
 $model = Bento::Meta::Model->new('Test');
 # pull model from database - add bolt connection with Neo4j::Bolt
 $model = Bento::Meta::Model->new('ICDC',Neo4j::Bolt->connect('bolt://localhost:7687))
 # connect model to db after creating 
 $model = Bento::Meta::Model->new('CTDC');
 $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
 $model->get(); # pulls nodes, properties, relationships with model => 'CTDC'

 # read a model from MDF YAML files:
 use Bento::Meta::MDF;
 $model = Bento::Meta::MDF->create_model(qw/icdc-model.yml icdc-model-props.yml/);
 # connect it and push to db
 $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
 $model->put(); # writes all to db

 # build model from scratch: add, change, and remove entities

 $model = Bento::Meta::Model->new('Test');
 
 # create some nodes and add them
 ($case, $sample, $file) = 
    map { Bento::Meta::Model::Node->new({handle => $_}) } qw/case sample file/;
 $model->add_node($case);
 $model->add_node($sample);
 $model->add_node($file);
 
 # create some relationships (edges) between nodes
 $of_case = Bento::Meta::Model::Edge->new({ 
   handle => 'of_case',
   src => $sample,
   dst => $case });
 
 $has_file = Bento::Meta::Model::Edge->new({
   handle => 'has_file',
   src => $sample,
   dst => $file });
   
 $model->add_edge($of_case);
 $model->add_edge($has_file);

 # create some properties and add to nodes or to edges
 $case_name = Bento::Meta::Model::Property->new({
   handle => 'name',
   value_domain => 'string' });
 $workflow_type = Bento::Meta::Model::Property->new({
   handle => 'workflow_type',
   value_domain => 'value_set' });

 $model->add_prop( $case => $case_name );
 $model->add_prop( $has_file => $workflow_type );

 # add some terms to a property with a value set (i.e., enum)

 $model->add_terms( $workflow_type => qw/wdl cwl snakemake/ );
  
=head1 DESCRIPTION

L<Bento::Meta::Model> provides an object representation of a single
L<property
graph|https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph>-based
data model, as embodied in the structure of the L<Bento Metamodel
Database|https://github.com/CBIIT/bento-mdf> (MDB). The MDB can store
multiple such models in terms of their nodes, relationships, and
properties. The MDB links these entities according to the structure of
the individual models. For example, model nodes are represented as
metamodel nodes of type "node", model relationships as metamodel nodes
of type "relationship", that themselves link to the relevant source
and destination metamodel nodes, representing the two end nodes in the
model itself. L<Bento::Meta::Model> can create, read, update, and link
these entities together according to the L<MDB
structure|https://github.com/CBIIT/bento-meta#structure>.

The MDB also provides entities for defining and maintaining
terminology associated with the stored models. These include the
C<term>s themselves, their C<origin>, and associated C<concept>s. Each
of these entities can be created, read, and updated using
L<Bento::Meta::Model> and the component objects.

=head2 A Note on "Nodes"

The metamodel is a property graph, designed to store specific property
graph models, in a database built for property graphs. The word "node"
is therefore used in different contexts and can be confusing,
especially since the Cancer Research Data Commons is also set up in
terms of "nodes", which are central repositories of cancer data of
different kinds. This and related documentation will attempt to
distinguish these concepts as follows.

=over 

=item * A "graph node" is a instance of the node concept in the
property graph model, that usually represents a category or item of
interest in the real world, and has associate properties that
distinguish it from other instances.

=item * A "model node" is a graph node within a specific data model, and represents groups of data items (properties) and can be related to other model nodes via model relationships. 

=item * A "metamodel node" is a graph node that represents a model node, model 
relationship, or model property, in the metamodel database.

=item * A "Neo4j node" refers generically to the representation of a node in the Neo4j database engine.

=item * A "CRDC node" refers to a data commons repository that is part of the CRDC, such as the L<ICDC|https://caninecommons.cancer.gov/#/>.

=back

=head2 A Note on Objects, Properties, and Attributes

L<Bento::Meta> creates a mapping between Neo4j nodes and Perl
objects. Of course, the objects have data associated with them,
accessed via setters and getters. These object-associated data are
referred to exclusively as "attributes" in the documentation.

Thus, a C<Bento::...::Node> object has an attribute C<props>
(properties), which is an (associative) array of
C<Bento::...::Property> objects. The C<props> attribute is a
representation of the C<has_property> relationships between the
metamodel node-type node to its metamodel property-type nodes.

See L<below|/Object attributes> for more details.

=head2 Working with Models

Each model stored in the MDB has a simple name, or handle. The word
"handle" is used throughout the metamodel to distinguish internal
names (strings that are used within the system and downstream
applications to refer to entities) and the external "terms" that are
employed by users and standards. Handles can be understood as "local
vocabulary". The handle is usually the name of the CRDC node that the
model supports.

A L<Bento::Meta::Model> object is meant to represent only one model. The 
L<Bento::Meta> object can contain and retrieve a number of models.

=head2 Component Objects

Individual entities in the MDB - nodes, relationships, properties,
value sets, terms, concepts, and origins, are represented by instances
of corresponding L<Bento::Meta::Model::Entity> subclasses:

=over

=item L<Bento::Meta::Model::Node>

=item L<Bento::Meta::Model::Edge>

("Edge" is easier to type than "relationship".)

=item L<Bento::Meta::Model::Property>

=item L<Bento::Meta::Model::ValueSet>

=item L<Bento::Meta::Model::Term>

=item L<Bento::Meta::Model::Concept>

=item L<Bento::Meta::Model::Origin>

=back

C<Bento::Meta::Model> methods generally accept these objects as
arguments and/or return these objects. To obtain specific scalar
information (for example, the handle string) of the object, use the
relevant getter on the object itself:

  # print the 'handle' for every property in the model
  for ($model->props) {
    say $_->handle;
  }

=head3 Object attributes

A node in the graph database can possess two kinds of related data. In
the (Neo4j) database, node "properties" are named items of scalar
data. These belong directly to the individual nodes, and are
referenced via the node. These map very naturally to scalar attributes
of a model object. For example, "handle" is a metamodel node property,
and it is accessed simply by the object attribute of the same name,
$node-E<gt>handle(). In the code, these are referred to as "property
attributes" or "scalar-valued attributes".

The other kind of data related to a given node is present in other nodes
that are linked to it via graph database relationships. In the
MDB, for example, a model edge (e.g., "of_sample") is represented by
its own graph node of type "Relationship", and the source and
destination nodes for that edge are two graph nodes of type "Node",
one of which is linked to the Relationship node with a graph
relationship "has_src", and the other with a graph relationship
"has_dst". (Refer to L<this
diagram|https://github.com/CBIIT/bento-meta#structure>.)

In the object model, the source and destination nodes of an edge are
also represented as object attributes: in this case, $edge-E<gt>src
and $edge-E<gt>dst. This representation encapsulates the "has_src" and
"has_dst" graph relationships, so that the programmer can ignore the
metamodel structure and concentrate on the model structure. Note that
the value of such an attribute is an object (or an array of objects).
In the code, such attributes are referred to as "relationship",
"object-valued" or "collection-valued" attributes.

=head3 Object interface

Individual objects have their own interfaces, which are partially described
in L</METHODS> below. Essentially, the name of the attribute is the 
name of the getter, while "set_<name>" is the setter. Getter return 
types depend on whether the attribute is scalar, object, or collection-valued.
Setter arguments have similar dependencies.

  For an attribute "blarg":

                     getter                            setter
  scalar-valued      blarg() returns scalar            set_blarg($scalar)
  object-valued      blarg() returns object            set_blarg($obj)
  collection-valued  blarg() returns array of objects  set_blarg(key => $obj)
                     blarg(key) returns object

A true array is returned by collection-valued getters, not an arrayref.

Collection-valued attributes are generally associative arrays. The key 
is the handle() of the subordinate object (or value() in the case of 
L<term|Bento::Meta::Model::Term> objects).

More details about objects can be found in L<Bento::Meta::Model::Entity>.
  
=head2 Model as Container

The Model object is a direct container of nodes, edges (relationships), and
properties. To get a simple list of all relevant entities in a model, use the
model getters:

  @nodes = $model->nodes();

To retrieve a specific entity, provide a key to the getter as the argument. 
The keys are laid out as follows

  Entity    Key                              Example
  ------    ---                              -------
  Node      <node handle>                    sample
  Property  <node handle>:<property handle>  sample:sample_type
  Edge      <edge handle>:<src node handle>:<dst node handle>
                                             of_sample:sample:case

For example:

  $of_sample = $model->edges('of_sample:sample:case');
  # get source and destination node objects from edge object itself
  $sample = $of_sample->src;
  $case = $of_sample->dst;

Note that the keys for edges are three strings separated by colons.
These are 1) the edge handle ("type"), 2) the source node handle, and
3) the destination node handle. In the example above, this is 
"of_sample:sample:case". This is called a "triplet" in the code. 
An edge object can be queried for its triplet.

  $edge->triplet

The component objects are themselves containers of their own
attributes, and their getters and setters are structured
similarly. (In fact, C<Bento::Meta::Model> is, like the component
objects, a subclass of L<Bento::Meta::Model::Entity>). The difference
is that keys for collection-valued attributes at the component object
level are simpler. For example:

  $prop1 = $model->props('sample:sample_type');
  $prop2 = $sample->props('sample_type');
  # $prop1 and $prop2 are the same object

=head3 Accessing other objects

The Model object does not provide access to C<Concept>, C<ValueSet>, or 
C<Origin> objects directly. These are accessible via the linked obects
themselves, according to the L<metamodel structure|https://github.com/CBIIT/bento-meta#structure>. For example:

  # all terms for all nodes
  for ($model->nodes) {
    push @node_terms, $_->concept->terms;
  }

=head2 Model as an Interface

The Model object has methods that allow the user to add, remove and
modify entities in the model. The Model object is an interface, in
that loosely encapsulates the MDB structure and tries to relieve the
user from having to remember that structure and guards against
deviations from it. 

The main methods are 

=over

=item * add_node()

=item * add_edge()

=item * add_prop()

=item * add_terms()

=item * rm_node()

=item * rm_edge()

=item * rm_prop()

=item * rm_terms() (coming soon)

=back

Details are below in L</$model object>. The main idea is that these
methods operate on either the relevant component object or on a
hashref that specifies an object by its attributes. In the latter
case, a new component object is created.

Here's a pattern for creating two nodes and an edge in a model:

  $src_node = $model->add_node({ handle => 'sample' });
  $dst_node = $model->add_node({ handle => 'case' });
  $edge = $model->add_edge({ handle => 'of_case',
                                src => $src_node,
                                dst => $dst_node });

These new entities are registered in the model, and can be retrieved:

  $case = $model->nodes('case'); # same obj as $dst_node
  $of_case = $model->edges('of_case:sample:case'); # same obj as $edge

Removing entities from the model "deregisters" them, but does not destroy
the object itself. 
 
  $case = $model->rm_node($case);
  $other_model->add_node($case);

Analogous to Neo4j, attempting to remove a node will throw, if the node 
participates in any relationships/edges. For the above to work, for example,
would require

  $model->rm_edge($of_case);

first.

=head3 Manipulating Terms

One of the key uses of the MDB is for storing lists of acceptable values for
properties that require them. In the MDB schema, a property is linked to 
a value set entity, and the value set aggregates the term entities. The model
object tries to hide some of this structure. It will also create a set of 
Term objects from a list of strings as a shortcut. 

  $prop = $model->add_prop( $sample => { handle => 'sample_type',
                                         value_domain => 'value_set' });
  # $prop has domain of 'value_set', so you can add terms to it
  $value_set = $model->add_terms( $prop => qw/normal tumor/ );
  @terms = $value_set->terms; # set of 2 term objects
  @same_terms = $prop->terms; # prop object also has a shortcut 

=head2 Database Interaction

The approach to the back and forth between the object representation
and the database attempts to be simple and robust. The pattern is a
push/pull cycle to and from the database. The database instrumentation
is also encapsulated from the rest of the object functionality, so
that even if no database is specified or connected, all the object
manipulations are available.

The Model methods are L<get()|/Database Interaction> and
L<put()|/Database Interaction>. C<get()> pulls the metamodel nodes for
the model with handle C<$model-E<gt>handle> from the connected
database. It will not disturb any modifications made to objects in the
program, unless called with a true argument. In that case, C<get(1)>
(e.g.) will refresh all objects from current metamodel nodes in the
database.

C<put()> pushes the model objects, with any changes to attributes, to
the database. It will build and execute queries correctly to convert, for
example, collection attributes to multiple nodes and corresponding
relationships. C<put()> adds and removes relationships in the database as
necessary, but will not fully delete nodes. To completely remove objects
from the database, use C<rm()> on the objects themselves:

  $edge = $model->rm_edge($edge); # edge detached from nodes and removed 
                                  # from model
  $model->put(); # metamodel node representing the edge is still present in db
                 # but is detached from the source node and destination node
  $node->rm(); # metamodel node representing the edge is deleted from db

=head1 METHODS

=head2 $model object

=head3 Write methods

=over

=item new($handle)

=item add_node($node_or_init)

=item add_edge($edge_or_init)

=item add_prop($node_or_edge, $prop_or_init)

=item add_terms($prop, @terms_or_inits)

=item rm_node($node)

=item rm_edge($edge)

=item rm_prop($prop)

=back

=head3 Read methods

=over

=item @nodes = $model->nodes()

=item $node = $model->node($name)

=item @props = $model->props()

=item $prop = $model->prop($name)

=item $edge = $model->edge($triplet)

=item @edges = $model->edges_in($node)

=item @edges = $model->edges_out($node)

=item @edges = $model->edge_by_src()

=item @edges = $model->edge_by_dst()

=item @edges = $model->edge_by_type()

=back

=head3 Database methods

=over

=item get()

Pull metamodel nodes from database for the model (given by $model-E<gt>handle)
Refresh nodes (reset) by issuing $model-E<gt>get(1). 

=item put()

Push model changes back to database. This operation will disconnect (remove
Neo4j relationships) nodes, but will not delete nodes themselves.

=back

=head2 $node object

=over

=item $node->name()

=item $node->category()

=item @props = $node->props()

=item $prop = $node->props($name)

=item @tags = $node->tags()

=back

=head2 $edge object

=over

=item $edge->type()

=item $edge->name()

=item $edge->is_required()

=item $node = $edge->src()

=item $node = $edge->dst()

=item @props = $edge->props()

=item $prop = $edge->props($name)

=item @tags = $edge->tags()

=back

=head2 $prop object

=over

=item $prop->name()

=item $prop->is_required()

=item $value_type = $prop->type()

=item @acceptable_values = $prop->values()

=item @tags = $prop->tags()

=back

=cut

1;
