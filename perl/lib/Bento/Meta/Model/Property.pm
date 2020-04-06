package Bento::Meta::Model::Property;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use Clone qw/clone/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => $handle,
    _model => undef,
    _value_domain => undef,
    _units => undef,
    _type => undef,
    _value_set => undef, # prop has_value_set value_set
    _entities => [], # entity | entity has_property prop
    _tags => [],
    _propdef => {}
   }, $init );

  $self->{_name} = $name;
  if ($propdef) {
    $self->{_propdef} = clone($propdef); # grab everything for later
    $self->{_is_required} = $propdef->{Req};
    if ($propdef->{Tags}) {
      $self->{_tags} = $propdef->{Tags};
    }
    # just return whatever is there, rather than normalize to string
    $self->{_type} = $propdef->{Type} ; # && (ref $propdef->{Type} ? ref $propdef->{Type} :
    #                                            $propdef->{Type});
    
    unless ( $self->{_type} ) {
      WARN "Property '$name' has no Type defined";
    }
    # below -- should call STS to get list if appropriate
    $self->{_values} = (ref $self->{_type} eq 'ARRAY' ? [@{$propdef->{Type}}] : undef );
  }
  else {
    WARN "Property '$name' does not have a PropDefinitions entry";
    $model->{_props}{$name} = $self;
  }
  return $self
}

sub values { $_[0]->{_values} && (ref $_[0]->{_values} eq 'ARRAY' ? @{$_[0]->{_values}} : ($_[0]->{_values})) }
1;
