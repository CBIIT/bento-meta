package Bento::Meta::Model::Term;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new({
    _id => undef,
    _value => undef,
    _origin_id => undef,
    _origin_definition => undef,
    _concept => \undef, # term has_concept concept
  }, $init);
  return $self;
}

sub map_defn {
  return {
    label => 'term',
    simple => [
      [id => 'id'],
      [value => 'value'],
      [origin_id => 'origin_id'],
      [origin_definition => 'origin_definition'],
     ],
    object => [
      [ 'concept' => '<:represents',
        'Bento::Meta::Model::Concept' => 'concept' ],
     ],
    collection => [
     ]
   };
}
1;
