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
    $self->build_maps;
  }
  return $self;
}

sub bolt_cxn { shift->{_bolt_cxn} }

sub build_maps {
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
  $_->get() for (@n,@e,@p);
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
    $vs->set_handle( $self->handle.substr($vs->id,0,7) );
    $prop->set_value_set($vs)
  }
  $vs->set_terms($_ => $terms{$_}) for keys %terms;
  return $vs;
}

# rm_node( $node_or_handle )
# node must participate in no edges to be able to be removed (like neo4j)
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
  }
  return $self->set_nodes( $node->handle => undef );
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
  }
  my ($hdl,$src,$dst) = split /:/, $edge->triplet;
  delete $self->{_edge_table}{$hdl}{$src}{$dst};
  return $self->set_edges( $edge->triplet => undef );
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
    }
    elsif (ref($e) =~ /Node$/) { # a node prop
      $e->set_props( $prop->handle => undef );
      $self->prop( join(':',$e->handle,$prop->handle) => undef );
    }
  }
  return $prop; 
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
sub nodes { return $_[0]->node($_[1]) if @_ > 1; values %{shift->{_nodes}} }

sub prop { $_[0]->{_props}{$_[1]} }
sub props { return $_[0]->prop($_[1]) if @_ > 1; values %{shift->{_props}} }

#sub edge_types { values %{shift->{_edge_types}} }
#sub edge_type { $_[0]->{_edge_types}{$_[1]} }

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

Bento::Meta::Model - object bindings for Bento Metamodel DB

=head1 SYNOPSIS

$model = Bento::Meta::Model->new();

=head1 DESCRIPTION

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

=item @edges = $modee->edges_out($node)

=item @edges = $model->edge_by_src()

=item @edges = $model->edge_by_dst()

=item @edges = $model->edge_by_type()

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
