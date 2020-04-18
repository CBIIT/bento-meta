package Bento::Meta::Model::Property;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _model => undef,
    _value_domain => undef,
    _units => undef,
    _type => undef,
    _pattern => undef, 
    _value_set => \undef, # prop has_value_set value_set
    _entities => [], # entity | entity has_property prop
    _tags => [],
    _parent_handle => undef, # 
    _propdef => {}
   }, $init );
  return $self;
}

sub type { shift->{_value_domain} } # alias
sub values {
  my $self = shift;
  return unless $self->value_set;
  my @ret;
  for ($self->value_set->terms) {
    push @ret, $_->value;
  }
  return @ret;
}

sub terms {
  my $self = shift;
  return unless $self->value_set;
  return $self->value_set->terms;
}

sub set_terms {
  my $self = shift;
  return unless $self->value_set;
  return $self->value_set->set_terms(@_);
}

1;
