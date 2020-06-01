package Bento::Meta;
use Bento::Meta::Model;
use Bento::Meta::MDF;
use Try::Tiny;
use Log::Log4perl qw/:easy/;
use strict;
use warnings;
no warnings qw/regexp/;

our $VERSION = "0.2";

our $re_url = qr{^(?:https?|bolt)://};

sub new {
  my $class = shift;
  my $self = bless {
    _models => {},
   }, $class;

  return $self;
}

sub load_model {
  my $self = shift;
  my ($handle, @files) = @_;
  unless ($handle) {
    LOGCROAK "load_model: need arg1 (model handle)";
  }
  my $model;
  unless (@files) {
    LOGCROAK "load_model: need arg2 ... (MDF files/db endpoint)";
  }
  if ( $files[0] =~ /$re_url/ ) {
    unless (eval "require Neo4j::Bolt;1") {
      LOGCROAK "Connection to Neo4j requires Neo4j::Bolt package";
    }
    $model = Bento::Meta::Model->new($handle, Neo4j::Bolt->connect($files[0]));
  }
  else {
    $model = Bento::Meta::MDF->create_model($handle, @files);
  }

  return $self->{_models}{$handle} = $model;
}

# just get the list of models (model handles) in database - do not load them!
sub list_db_models {
  my $self = shift;
  my ($connection) = @_;

  # return value, will hold found models in db
  my @db_model_handles = ();

  # connect to neo4j
  my $bolt_cxn = Neo4j::Bolt->connect($connection);
  unless ($bolt_cxn->connected) {
      LOGDIE ref($self)."::get_db_handle : Can't connect! ".$bolt_cxn->errmsg; 
      return;
  }
  # retrieve all model handles from db
  my $qry = "MATCH (n:node) RETURN DISTINCT n.model";
  my $stream = $bolt_cxn->run_query($qry, {});
  while (my @results = $stream->fetch_next ) {
    push @db_model_handles, $results[0];
  }

  return @db_model_handles;
}

# load all the database models
sub load_all_db_models{
  my $self = shift;
  my ($connection) = @_;

  my @db_handles = $self->list_db_models($connection);

    foreach my $handle (@db_handles){
        $self->load_model($handle, $connection);
    }

  return @db_handles;
}

sub model { $_[0]->{_models}{$_[1]} };
sub models { values %{shift->{_models}} };
sub handles { sort keys %{shift->{_models}} };

1;

=head1 NAME

Bento::Meta - Tools for manipulating a Bento Metamodel Database

=head1 SYNOPSIS

=head1 DESCRIPTION

L<Bento::Meta> is a full object-relational mapping (although for a graph
database, L<Neo4j|https://neo4j.com>) of the Bento metamodel for storing
property graph representations of data models and terminology.

It can be also be used without a database connection to read, manipulate, 
and store data models in the 
L<Model Description Format|https://github.com/CBIIT/bento-mdf> (MDF). 

This class is just a L<Bento::Meta::Model> factory and container. 

=head1 METHODS

=over

=item load_model($handle, @files), load_model($handle, $bolt_url)

Load a model from MDF files, or from a Neo4j database. C<$bolt_url> must
use the C<bolt://> scheme.

=item list_db_models($bolt_url)

Lists all of the models found in a Neo4j database. C<$bolt_url> must
use the C<bolt://> scheme. 

=item load_all_db_models($bolt_url)

Loads all models found in a Neo4j database.  C<$bolt_url> must
use the C<bolt://> scheme. 

=item model($handle)

The L<Bento::Meta::Model> object corresponding to the handle.

=item models()

A list of L<Bento::Meta::Model> objects contained in the object.

=item handles()

A sorted list of model handles contained in the object.

=back

=head1 SEE ALSO

L<Bento::Meta::Model>, L<Neo4j::Bolt>.

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at nih -dot- gov>
 FNL

=cut
