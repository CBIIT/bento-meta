package Bento::Meta::Model;
use base Bento::Meta::Model::Entity;
use v5.10;
use lib '../../../lib';
use Bento::Meta::Model::Node;
use Bento::Meta::Model::Edge;
use Bento::Meta::Model::Property;
use Bento::Meta::Model::EdgeType;
use Bento::Meta::Model::Origin;
use Bento::Meta::Model::Concept;
use Bento::Meta::Model::Term;
use Carp qw/croak/;
use Log::Log4perl qw/:easy/;
use strict;

# new($handle)
sub new {
  my $class = shift;
  my ($handle) = @_;
  unless ($handle) {
    FATAL "Model::new() requires handle as arg1";
    croak;
  }
  DEBUG "Creating Model object with handle '$handle'";
  my $self = $class->SUPER::new({
    _handle => $handle,
    _nodes => {},
    _edges => {},
    _props => {},
    _edge_table => {},
   });
  return $self;
}

# create/delete API

# add_node( {handle =>'newnode', ...} ) or add_node($node)
# new node will be added to the Model nodes hash
sub add_node {
  my $self = shift;
  my ($init) = shift;
  if (ref($init) eq 'HASH') {
    $init = Bento::Meta::Model::Node->new($init);
  }
  unless ($init->handle) {
    FATAL ref($self)."::add_node - init hash reqs 'handle' key/value";
    die;
  }
  if (defined $self->nodes($init->handle)) {
    WARN ref($self)."::add_node : overwriting existing node with handle '".$init->handle."'";
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
  if (ref($init) eq 'HASH') {
    $init = Bento::Meta::Model::Edge->new($init);
  }
  unless ( $init->handle && $init->src && $init->dst ) {
    FATAL ref($self)."::add_edge - init hash reqs 'handle','src','dst' key/values";
    die;
  }
  if ($etbl->{$init->handle} &&
        $etbl->{$init->handle}{$init->src->handle} &&
        $etbl->{$init->handle}{$init->src->handle}{$init->dst->handle}) {
    WARN ref($self)."::add_edge : overwriting existing edge with handle/src/dest '".join("/",$init->handle, $init->src->handle, $init->dst->handle)."'";
  }
  $etbl->{$init->handle}{$init->src->handle}{$init->dst->handle} = $init;
  $self->set_props( join('.', $init->handle, $init->src->handle, $init->dst->handle) => $init );
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
    FATAL ref($self)."::add_prop - arg1 must be Node or Edge object";
    die;
  }
  unless (defined $init) {
    FATAL ref($self)."::add_prop - arg2 must be init hash or Property object";
    die;
  }
  if (ref($init) eq 'HASH') {
    $init = Bento::Meta::Model::Edge->new($init);
  }
  unless ($init->handle) {
    FATAL ref($self)."::add_prop - init hash (arg2) reqs 'handle' key/value";
    die;
  }
  my $pfx = join('.', $ent->handle, $ent->can('src') ? $ent->src->handle : (),
                 $ent->can('dst') ? $ent->dst->handle : ());
  if ( $self->props(join('.',$pfx,$init->handle)) ) {
    WARN ref($self)."::add_prop - overwriting existing prop '".join('.',$pfx,$init->handle)."'";
  }
  $ent->set_prop( $init->handle => $init );
  $self->set_props( join('.',$pfx,$init->handle) => $init );
}

# rm_node( $node_or_handle )
sub rm_node {}

# rm_prop( $prop_or_handle )
sub rm_prop {}

# rm_edge( $edge_or_sth_else )
sub rm_edge {}


# read API

sub node { $_[0]->{_nodes}{$_[1]} }
sub nodes { values %{shift->{_nodes}} }

sub prop { $_[0]->{_props}{$_[1]} }
sub props { values %{shift->{_props}} }

sub edge_types { values %{shift->{_edge_types}} }
sub edge_type { $_[0]->{_edge_types}{$_[1]} }

sub edges {  @{shift->{_edges}} }
sub edge {
  my $self = shift;
  my ($type,$src,$dst) = @_;
  $type = $type->name if ref $type;
  $src = $src->name if ref $src;
  $dst = $dst->name if ref $dst;
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
    FATAL "Model::edge_by() - arg 1 must be one of src|dst|type";
    exit 1;
  }
  if (ref($arg) =~ /Model/) {
    $arg = $arg->name;
  }
  elsif (ref $arg) {
    FATAL "arg must be a ".__PACKAGE__."-related object or string, not ".ref($arg);
    exit 1;
  }
  my @ret;
  for ($key) {
    /^src$/ && do {
      for my $t (keys %{$self->{_edge_table}}) {
        for my $u (keys %{$self->{_edge_table}{$t}{$arg}}) {
          push @ret, $self->{_edge_table}{$t}{$arg}{$u};
        }
      }
      last;
    };
    /^dst$/ && do {
      for my $t (keys %{$self->{_edge_table}}) {
        for my $u (keys %{$self->{_edge_table}{$t}}) {
          push @ret, $self->{_edge_table}{$t}{$u}{$arg};
        }
      }
      last;
    };
    /^type$/ && do {
      for my $t (keys %{$self->{_edge_table}{$arg}}) {
        for my $u (keys %{$self->{_edge_table}{$arg}{$t}}) {
          push @ret, $self->{_edge_table}{$arg}{$t}{$u};
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

=over

=item @nodes = $model->nodes()

=item $node = $model->node($name)

=item @props = $model->props()

=item $prop = $model->prop($name)

=item $edge_type = $model->edge_type($type)

=item @edge_types = $model->edge_types()

=item @edges = $model->edge_by_src()

=item @edges = $model->edge_by_dst()

=item @edges = $model->edge_by_type()

=back

=head2 $node object

=over


=item $node->name()

=item $node->category()

=item @props = $node->props()

=item $prop = $node->prop($name)

=item @tags = $node->tags()

=back

=head2 $prop object

=over

=item $prop->name()

=item $prop->is_required()

=item $value_type = $prop->type()

=item @acceptable_values = $prop->values()

=item @tags = $prop->tags()

=back

=head2 $edge_type object

=over

=item $edge_type->name()

=item $edge_type->multiplicity(), $edge_type->cardinality()

=item $prop = $edge_type->prop($name)

=item @props = $edge_type->props()

=item @allowed_ends = $edge_type->ends()

=item @tags = $edge_type->tags()

=back

=head2 $edge object

=over

=item $edge->type()

=item $edge->name()

=item $edge->is_required()

=item $node = $edge->src()

=item $node = $edge->dst()

=item @props = $edge->props()

=item $prop = $edge->prop($name)

=item @tags = $edge->tags()

=back

=cut

1;
