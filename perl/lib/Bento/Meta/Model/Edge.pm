package Bento::Meta::Model::Edge;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use Clone qw/clone/;
use strict;

# one edge per type:src:dst triplet
sub new {
  my $class = shift;
  my ($init) = @_;
  my $self =  $class->SUPER::new({
    _handle => undef,
    _model => undef,
    _multiplicity => undef,
    _src => undef,
    _dst => undef,
    _is_required => undef,
    _type => undef,
    _concept => undef,
    _tags => [],
    _props => {}, # prop | edge has_property prop (key: prop.handle)
    _edgedef => {},
  }, $init);

  my ($src,$dst);
  $self->{_edgedef} = clone($info);
  $self->{_type} = $model->edge_type($type);
  $self->{_name} = $self->{_type}->name;
  if ($info->{Tags}) {
    $self->{_tags} = $info->{Tags};
  }
  unless ($self->{_src} = $src = $info->{Src}) {
    WARN "An edge of type '$type' is missing source node spec";
  }
  unless ($self->{_dst} = $dst = $info->{Dst}) {
    WARN "An edge of type '$type' is missing destination node spec";
  }
  if ($model) {
    unless ($self->{_src} = $model->node($self->{_src})) {
      WARN "No node object defined yet with name '$$self{_src}' for an edge of type '$type'";
    }
    unless ($self->{_dst} = $model->node($self->{_dst})) {
      WARN "No node object defined yet with name '$$self{_dst}' for an edge of type '$type'";
    }
  }
  else {
    WARN "Edge constructor called without model object: src and dst are strings, not Node objects";
  }
  $model->{_edge_table}{$type}{$src}{$dst} //= $self;
  return $model->{_edge_table}{$type}{$src}{$dst};
}


1;
