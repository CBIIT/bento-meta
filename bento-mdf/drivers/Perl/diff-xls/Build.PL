use Module::Build;
my $build = Module::Build->new(
  dist_name => "diff-xls",
  dist_abstract => "Create Excel file diff between latest and earlier model flatfiles",
  dist_version_from => 'bin/flat-model-diff-xls.pl',
  dist_author => 'Mark A. Jensen',
  perl => '5.010',
  configure_requires => {
    'Module::Build' => 0,
  },
  build_requires => {
    'IPC::Run' => 0,
    'Test::Exception' => 0,
  },
  requires => {
    'IPC::Run' => 0,
    'Excel::Writer::XLSX' => 0,
    'Pod::Usage' => 0,
  },
 );

$build->add_to_cleanup("ctdc-model");
$build->create_build_script;

  
