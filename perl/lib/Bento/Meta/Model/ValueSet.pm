package Bento::Meta::Model::ValueSet;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _id => undef,
    _url => undef,
    _terms => {}, # term | value_set has_term term (key: term.value)
    _prop => \undef, # prop | prop has_value_set value_set
    _origin => \undef, # value_set has_origin origin
  },$init);
  return $self;
}

sub map_defn {
  return {
    label => 'value_set',
    simple => [
      [handle => 'handle'],
      [id => 'id'],
      [url => 'url'],
     ],
    object => [
      [ prop => '<:has_value_set',
        'Bento::Meta::Model::Property' => 'property' ],
      [ origin => ':has_origin>',
        'Bento::Meta::Model::Origin' => 'origin' ]
     ],
    collection => [
      [ terms => ':has_term>',
        'Bento::Meta::Model::Term' => 'term' ]
     ]
   };
}

1;
