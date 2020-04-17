package Bento::Meta::Model::Entity;
use Bento::Meta::Model::ObjectMap;
use UUID::Tiny qw/:std/;
use Log::Log4perl qw/:easy/;

use strict;
our $OBJECT_MAP;
our $AUTOLOAD;

our @common_attr = qw/
_desc
_dirty
_neoid
                     /;
sub new {
  my $class = shift;
  my ($attr,$init) = @_;
  my $self = bless $attr, $class;
  $self->{_dirty} = 1; # indicates change that has not been synced with db
  #                      0 => fully synced with db
  #                     -1 => simple-valued attr sync, object-valued attr not yet
  $self->{_neoid} = undef; # database id for this entity
  $self->{_desc} = undef; # free text description for entity

  my @declared_atts = map { /^_(.*)/;$1 } keys %$self;
  $self->{_declared} = \@declared_atts;

  if (defined $init) {
    unless (ref($init) =~ /^HASH|Neo4j::Bolt::Node$/) {
      LOGDIE "$class::new - arg1 must be a Neo4j::Bolt::Node or hashref of initial attr values";
    }
    $init = $init->{properties} if ref($init) eq 'Neo4j::Bolt::Node';
    for my $k (keys %$init) {
      if (grep /^$k$/, @declared_atts) {
        my $symb = "set_$k";
        $self->$symb($init->{$k});
      }
      else {
        LOGWARN "$class::new() - attribute '$k' in init not declared in object";
        $self->{"_$k"} = $init->{$k};
      }
    }
  }
  return $self;
}

# add an object map to the (subclassed) object
# and attach get, put as available methods to instances
sub object_map {
  my $class = shift;
  unless (!ref $class) {
    LOGDIE __PACKAGE__."::object_map : class method only";
  }
  my ($map) = @_;
  return if eval "\$${class}::OBJECT_MAP;";

  my $omap = Bento::Meta::Model::ObjectMap->new($class);
  for (@{$map->{simple}}) {
    $omap->map_simple_attr(@$_);
  }
  for (@{$map->{object}}) {
    $omap->map_object_attr(@$_);
  }
  for (@{$map->{collection}}) {
    $omap->map_collection_attr(@$_);
  }
  eval qq|
  \$${class}::OBJECT_MAP = \$omap
|;
  eval qq|
 *${class}::get = sub { \$${class}::OBJECT_MAP->get( shift, \@_ ) }
|;
  return $omap;
}

# any object can poop a uuid if needed
sub make_uuid { create_uuid_as_string(UUID_V4) };

sub AUTOLOAD {
  my $self = shift;
  my @args = @_;
  my $method = $AUTOLOAD =~ s/.*:://r;
  my $set = $method =~ s/^set_//;
  if (grep /^$method$/, @{$self->{_declared}}) {
    my $att = $self->{"_$method"};
    if (!$set) { # getter
      for (ref $att) {
        /^ARRAY$/ && do {
          return @$att;
        };
        /^HASH$/ && do {
          if ($args[0]) {
            return $att->{$args[0]};
          }
          else {
            return wantarray ? values %$att : $att;
          }
        };
        do {
          return $att;
        };
      }
    }
    else { #setter
      return unless @args;
      for (ref $att) {
        /^ARRAY$/ && do {
          unless (ref $args[0] eq 'ARRAY') {
            FATAL "set_$method requires arrayref as arg1";
            die;
          }
          $self->{_dirty} = 1;
          return $self->{"_$method"} = $args[0];
        };
        /^HASH$/ && do {
          if (ref $args[0] eq 'HASH') {
            $self->{_dirty} = 1;
            return $self->{"_$method"} = $args[0];
          }
          elsif (!ref($args[0]) && @args > 1) {
            $self->{_dirty} = 1;
            if (defined $args[1]) {
              return $self->{"_$method"}{$args[0]} = $args[1];
            }
            else { # 2nd arg is explicit undef - means delete
              return delete $self->{"_$method"}{$args[0]}
            }
          }
          else {
            FATAL "set_$method requires hashref as arg1, or key => value as arg1 and arg2";
            die;
          }
        };
        do { # scalar attribute
          $self->{_dirty} = 1;
          return $self->{"_$method"} = $args[0];
        };
      }
    }
  }
  else {
    LOGDIE "Method '$method' undefined for ".ref($self);
  }
}

sub attrs { @{shift->{_declared}} }
sub atype { ref shift->{"_".shift} }
sub name { shift->{_handle} }

sub DESTROY {
  my $self = shift;
  for (keys %$self) {
    undef $self->{$_};
  }
  return;
}

=head1 NAME

Bento::Meta::Model::Entity - base class for model objects

=head1 SYNOPSIS

 package Bento::Meta::Model::Object;
 use base Bento::Meta::Model::Entity;
 use strict;
 
 sub new {
   my $class = shift;
   my ($init_hash) = @_;
   my $self = $class->SUPER::new( {
     _my_scalar_attr => undef,
     _my_array_attr => [],
     _my_hash_attr => {},
     }, $init );
 }

 use Bento::Meta::Model::Object;
 $o = Bento::Meta::Model::Object->new({
  my_scalar_attr => 1,
  my_array_attr => [qw/ a b c /],
  my_hash_attr => { yet => 0, another => 1, hashref => 2},
 });

 # getters
 $value = $o->my_scalar_attr;  # get scalar value
 @values = $o->my_array_attr;  # get array (not ref)
 $hash_value = $o->my_hash_attr; # get hashref, but prefer this:
 $value_for_key = $o->my_hash_attr( $key ); # get hash value for key, or
 @hash_values = $o->my_hash_attr; # in array context, returns hash values as array

 # setters
 $new_value = $o->set_my_scalar_attr("new value!"); # set scalar
 $o->set_my_array_attr( [ qw/ arrayref with some values / ] ); # replace arrayref
 $o->set_my_hash_attr( key => $value ); # set a value for a key in hash attr
 $o->set_my_hash_attr( { brand => 1, new => 2, hashref => 3 }); # replace hashref 

=head1 DESCRIPTION

Bento::Meta::Model::Entity is a base class that allows quick and dirty setup
of model objects and provides a consistent interface to simple attributes.
See L</SYNOPSIS>.

It also provides a place for common actions that must occur for OGM bookkeeping.

You can override anything in the subclasses and make them as complicated as 
you want. 

=head1 METHODS

=over

=item new($attr_hash, $init_hash)

=item make_uuid()

Create a new uuid (with L<Data::UUID>).
Doesn't put it anywhere, just returns it.

=item attrs()

Returns list of attributes declared for this object. 

=item atype($attr)

Return type (undef => scalar, 'ARRAY', or 'HASH') of the attribute $attr.

=head1 AUTHOR

 Mark A. Jensen (mark -dot- jensen -at- nih -dot- gov)
 FNL

=cut




1;
