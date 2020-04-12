package Bento::Meta::Model::ObjectMap;
use Scalar::Util qw/blessed/;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($obj_class) = @_;
  unless ($obj_class) {
    LOGDIE "${class}::new : require an object class (string) for arg1";
  }
  # ck obj_class
  my ($label) = $obj_class =~ /::([^:]+)$/;
  my $self = bless {
    _class => $obj_class,
    _label => lc $label,
    _property_map => {},
    _relationship_map => {},
   }, $class;
  
  return $self;
}


sub class { shift->{_class} }
sub label { shift->{_label} }
sub pmap { shift->{_property_map} }
sub rmap { shift->{_relationship_map} }

sub property_attrs {
  return keys %{ shift->pmap }
}

sub relationship_attrs {
  return keys %{ shift->rmap }
}

sub map_simple_attr {
  my $self = shift;
  my ($attr, $property) = @_;
  # ck args
  return $self->{_property_map}{$attr} = $property;
}1;


sub map_object_attr {
  my $self = shift;
  my ($attr, $relationship, $end_label) = @_;
  # ck args
  return $self->{_relationship_map}{$attr} = [$relationship,$end_label,0];
}1;

sub map_collection_attr {
  my $self = shift;
  my ($attr, $relationship, $end_label) = @_;
  # ck args
  return $self->{_relationship_map}{$attr} = [$relationship, $end_label,1];
}1;

# cypher query to pull a node
sub get_q {
  my $self = shift;
  my ($obj) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::get_q : arg1 must be an object of class ".$self->class;
  }
  
  if ($obj->neoid) {
    return cypher->match('n:'.$self->label)
      ->where( { 'id(n)' => $obj->neoid })
      ->return('n');
  }
  # else, find equivalent node
  my $wh = {};
  for ($self->property_attrs) {
    $wh->{$self->pmap->{$_}} = $obj->$_;
  }
  return cypher->match('n:'.$self->label)
    ->where($wh)
    ->return('n');
}

# cypher query to pull nodes via relationship
sub get_attr_q {
  my $self = shift;
  my ($obj,$att) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::get_attr_q : arg1 must be an object of class ".$self->class;
  }
  unless ($att) {
    LOGDIE ref($self)."::get_attr_q : arg2 must be an attribute name for class ".$self->class;
  }
  # set up obj match:
  my $q = $self->get_q($obj);
  # hack Cypher::Abstract - drop the return and add a with: 
  pop @{$q->{stack}};
  $q->with('n');
  # note: the relationship is non-directional in the query
  if ( grep /^$att$/, $self->property_attrs ) {
    $q->return( 'n.'.$self->pmap->{$att} );
  }
  elsif (grep /^$att$/, $self->relationship_attrs ) {
    my ($reln, $end_label, $many) = @{$self->rmap->{$att}};
    $q->match(ptn->N('n')->R(":$reln")->N('a:'.$end_label))->
      return('a');
    $q->limit(1) unless $many;
    return $q;
  }
  else {
    LOGDIE ref($self)."::get_attr_q : '$att' is not a registered attribute for class ".$self->class;
  }
}

# put_q
# if obj has a neoid (is 'mapped'), then overwrite the props on that node
# in the DB with the props in the obj
# if obj does not have a neoid, create a new node with the props on the object
# both stmts return the node id
sub put_q {
  my $self = shift;
  my ($obj) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::put_q : arg1 must be an object of class ".$self->class;
  }
  my $props = {};
  my @null_props;
  for ($self->property_attrs) {
    if (defined $obj->$_) {
      $props->{$self->pmap->{$_}} = $obj->$_;
    }
    else {
      push @null_props, $self->pmap->{$_};
    }
  }
  
  if ($obj->neoid) {
  # rewrite props on existing node
  # need to set props that have defined values,
  # and remove props that undefined values -
  # so 2 statements are returned
    my @stmts;
    push @stmts, cypher->match('n:'.$self->label)
      ->where({ 'id(n)' => $obj->neoid })
      ->set($props)
      ->return('id(n)');
    for (@null_props) {
      push @stmts, cypher->match('n:'.$self->label)
        ->where({ 'id(n)' => $obj->neoid })
        ->remove('n.'.$_)
        ->return('id(n)');
    }
    return @stmts;
  }
  # else, create new node with props that have defined values
  return cypher->create(ptn->N('n:'.$self->label => $props))
    ->return('id(n)');
}

# put_attr_q($obj, $attr => @values)
# - query to create relationships and end nodes corresponding
# to object- or collection-valued attributes
# can only do this on node that already is mapped in the db (must have non-empty
# neoid() attr)
# for each obj in @values - require these all be present in db as well? Or create de novo?
# - require that they be mapped: do put_q($_) for (@values), then put_attr_q,
# if necessary
sub put_attr_q {
  my $self = shift;
  my ($obj,$att, @values) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::put_attr_q : arg1 must be an object of class ".$self->class;
  }
  unless (defined $obj->neoid) {
    LOGDIE ref($self)."::put_attr_q : arg1 must be a mapped object (attr 'neoid' must be set)";  }
  unless (@values) {
    LOGDIE ref($self)."::put_attr_q : arg2,... must be a list of endpoint objects";
  }
  if ( grep /^$att$/, $self->property_attrs ) {
    return cypher->match('n:'.$self->label)
      ->where({'id(n)' => $obj->neoid })
      ->set( {'n.'.$self->pmap->{$att} => $values[0]} )
      ->return('id(n)');
  }
  elsif (grep /^$att$/, $self->relationship_attrs ) {
    my ($reln, $end_label, $many) = @{$self->rmap->{$att}};
    my @stmts;
    for my $val (@values) {
      unless (blessed $val && $val->isa('Bento::Meta::Model::Entity')) {
        LOGDIE ref($self)."::put_attr_q : arg 3,... must all be Entity objects";
      }
      unless ($val->neoid) {
        LOGDIE ref($self)."::put_attr_q : arg 3,... must all be mapped objects (all must have 'neoid' set)";
      }
      my $q = cypher->match('n:'.$self->label)
        ->where({'id(n)' => $obj->neoid })
        ->with('n')
        ->merge(ptn->N('n')->R(":$reln")->N('a:'.$end_label))
        ->where({'id(a)' => $val->neoid})
        ->return('id(a)');
      push @stmts, $q;
      last unless $many;
    }
    return @stmts;
  }
  else {
    LOGDIE ref($self)."::put_attr_q : '$att' is not a registered attribute for class ".$self->class;
  }
}

=head1 NAME

Bento::Meta::Model::ObjectMap - interface Perl objects with Neo4j database

=head1 SYNOPSIS

  # create object map for class
  $map = Bento::Meta::Model::ObjectMap->new('Bento::Meta::Model::Node')
  # map object attributes to Neo4j model 
  #  simple attrs = properties
  for my $p (qw/handle model category/) {
    $map->map_simple_attr($p => $p);
  }
  #  object- or collection-valued attrs = relationships to other nodes
  $map->map_object_attr('concept' => 'has_concept', 'concept');
  $map->map_collection_attr('props' => 'has_property', 'property');

  # use the map to generate canned cypher queries

=head1 DESCRIPTION

=head1 METHODS

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

1;
