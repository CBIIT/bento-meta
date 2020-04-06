package Bento::Meta::Model::EdgeType;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use Clone qw/clone/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _model => undef,
    _tags => [],
    _props => {},
    _ends => [],
    _edgedef => {},
  }, $init);

  $self->{_name} = $type;
  if ($info->{Tags}) {
    $self->{_tags} = $info->{Tags};
  }
  for my $p (@{ $info->{Props} }) {
    $self->{_props}{$p} = $model->prop($p) || Bento::Meta::Model::Property->new($p,undef,$model);
  }
  $self->{_edgedef} = clone( $info );
  for (@{$info->{Ends}}) {
    my $src = $_->{Src};
    my $dst = $_->{Dst};
    WARN "No 'Src' in 'Ends' entry for edge type '$type'" unless ($src);
    WARN "No 'Dst' in 'Ends' entry for edge type '$type'" unless ($dst);
    if ($model->node($src)) {
      $src = $model->node($src);
    }
    else {
      WARN "No source node '$src' defined in Nodes for Ends entry in edge type '$type'";
      $src = Bento::Meta::Model::Node->new($src, undef, $model);
    }
    if ($model->node($dst)) {
      $dst = $model->node($dst);
    }
    else {
      WARN "No source node '$dst' defined in Nodes for Ends entry in edge type '$type'";
      $dst = Bento::MakeModel::Model::Node->new($dst, undef, $model);
    }
    push @{$self->{_ends}}, {Src => $src, Dst => $dst};
  }
  return $self;
}
sub tags { @{shift->{_tags}} }
sub name { shift->{_name} }
sub props { values %{shift->{_props}} }
sub prop { $_[0]->{_props}{$_[1]} }
sub ends { @{shift->{_ends}} }
sub multiplicity { shift->{_edgedef}->{Mul} }
sub cardinality { shift->multiplicity }

1;
