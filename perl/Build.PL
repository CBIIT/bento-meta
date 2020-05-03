use Module::Build;

my $class = Module::Build->subclass(
  class => 'Builder',
  code => <<'CODE',
use File::Find;
sub ACTION_author_tasks {
  my $self = shift;
  my ($action, $subaction) = @ARGV;
  if ($subaction && ($subaction eq 'readme')) {
    unless (eval "require Pod::Markdown; 1") {
      print "Don't have Pod::Markdown\n";
      return;
    }
    # write POD as <Module>.md in relevant lib/ subdirs
    find (
      sub {
        return unless $_ =~ /^(.*)\.pm$/;
        my ($name) = $1;
        die unless defined $name;
        my $mdstr = '';
        my $p2m = Pod::Markdown->new();
        $p2m->local_module_url_prefix('github::');
        $p2m->local_module_re(qr/^Bento::/);
        $p2m->output_string(\$mdstr);
        $p2m->parse_file($_);
        $mdstr =~ s/%3A%3A/::/g;
        $mdstr =~ s{(\][(]github::[^)]*[)])}
                   {
                     $_ = $1;
                     s|github::|/perl/lib/|;
                     s|::|/|g;
                     s|[)]$|.md)|;
                     $_
                   }eg;
        if (length $mdstr > 1) {
          open my $mdf, '>', "$name.md" or die $!;
          print $mdf $mdstr;
          close $mdf;
        }
      },
      File::Spec->catdir($self->base_dir,'lib')
       );
     
  } else {
    print STDERR "Valid author tasks are:\n\treadme\n";
    exit 1;
  }
  # use the dist-version-from .pm's .md as README.md
  if ($self->dist_version_from && 0) {
    my $mdf = $self->dist_version_from;
    $mdf =~ s/\.pm/\.md/;
    $self->copy_if_modified( from => $mdf, to => 'README.md' );
  }
}
CODE
);

my $build = $class->new(
  dist_name => 'Bento-Meta',
  dist_abstract => 'Tools for manipulating a Bento Metamodel Database',
  dist_version_from => 'lib/Bento/Meta.pm',
  dist_author => 'Mark A. Jensen',
  perl => '5.010',
  configure_requires => {
    'Module::Build' => 0,
  },
  build_requires => {
    'Test::Exception' => 0,
    'Test::Warn' => 0,
    'IPC::Run' => 0,
    'IO::Pty' => 0,
  },
  requires => {
    'Log::Log4perl' => 0,
    'Try::Tiny' => 0,
    'UUID::Tiny' => 0,
    'Scalar::Util' => 0,
    'JSON::ize' => '>= 0.202',
    'YAML::PP' => '>= 0.018',
    'Hash::Merge' => '>= 0.300',
    'Neo4j::Cypher::Abstract' => '>=0.1003',
    'Neo4j::Bolt' => '>=0.12',
   },
  
 );

$build->create_build_script;
