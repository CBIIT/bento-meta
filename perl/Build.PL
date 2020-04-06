use Module::Build;

my $build = Module::Build->new(
  dist_name => 'Bento-MDB',
  dist_abstract => 'Tools for manipulating Bento Metamodel Database',
  dist_version_from => 'lib/Bento/MDB.pm',
  dist_author => 'Mark A. Jensen',
  perl => '5.010',
  configure_requires => {
    'Module::Build' => 0,
   },
  requires => {
    'Bento::MakeModel' => 0,
   },
  
 );

$build->create_build_script;
