package Bento::Meta::Model::Origin;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _name => undef,
    _url => undef,
    _is_external => undef,
    _entities => [], # entity | entity has_origin origin
  }, $init );
  
  return $self;
}

sub map_defn {
  return {
    label => 'origin',
    simple => [
      [ id => 'id' ],
      [ name => 'name'],
      [ url => 'url'],
      [ is_external => 'is_external'],
     ],
    object => [
     ],
    collection => [
      [ 'entities' => ':>',
        ['Bento::Meta::Model::ValueSet',
         'Bento::Meta::Model::Term'] => '' ]
     ]
   };
}1;

=head1 NAME

Bento::Meta::Model::Origin - object that models a term's authoritative source

=head1 SYNOPSIS

=head1 DESCRIPTION

=head1 METHODS

=over

=item name(), set_name($origin_name)

=item url(), set_url($url)

Ideally, the official URL for the authority or source.

=item is_external, set_is_external($bool)

Source is external to the orginization running the MDB.

=item @entities = $origin->entities()

Terms or value sets which have this origin, source or authority.

=back

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

1;
