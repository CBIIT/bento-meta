use Module::Build;

my $build = Module::Build->new(
  dist_name => 'Bento-Meta',
  dist_abstract => 'Tools for manipulating Bento Metamodel Database',
  dist_version_from => 'lib/Bento/Meta.pm',
  dist_author => 'Mark A. Jensen',
  perl => '5.010',
  configure_requires => {
    'Module::Build' => 0,
  },
  build_requires => {
    'Test::Exception' => 0,
    'Test::Warn' => 0,
  },
  requires => {
    'Log::Log4perl' => 0,
    'Try::Tiny' => 0,
    'Scalar::Util' => 0,
    'JSON::ize' => '>= 0.202',
    'YAML::PP' => '>= 0.018',
    'Hash::Merge' => '>= 0.300',
   },
  
 );

$build->create_build_script;
