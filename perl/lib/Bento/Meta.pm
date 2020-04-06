package Bento::Meta;
use Bento::MakeModel;
use Try::Tiny;
use Carp qw/carp croak/;
use strict;
use warnings;

our $VERSION = "0.1";

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
    croak "load_model: need arg1 (model handle)";
  }
  unless (@files) {
    croak "load_model: need arg2 ... (MDF files/db endpoint)";
  }
  return $self->load_model_from_db(@_) if ( $files[0] =~ /$re_url/ );
  my $mm;
  try {
    $mm = Bento::MakeModel->new(files => \@files);
  } catch {
    croak "load_model: Bento::MakeModel::new(): $_";
  };
  $self->{_models}{$handle} = $mm->model;
  return $self;
}

sub load_model_from_db {
  my $self = shift;
  my ($handle, $url) = @_;
  unless ($handle && $url) {
    croak "load_model_from_db: need arg1 (model handle) and arg2 (url-db endpt)";
  }
  carp "unimplemented";
  return 0;
}

sub model { $_[0]->{_models}{$_[1]} };
1;
