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
      ->where({'id(n)' => $obj->neoid })
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

  
1;
