# new-repo-setup
# after setting up a new model repo and pulling bento-mdf as a submodule:
# run in the root dir
# $ python bento-mdf/setup/new-repo-setup.py

# Create .travis.yml from template, put in top-level dir
# Create README.md.content from template
# Create docs dir (if not yet there) - populate with
# - setup/_config.yml
# - setup/assets
# - README.md.content

# variables needed:
# base: basename of the repo - like "icdc-model"
# mdfs: list of the MDFs - like ['icdc-model.yml', 'icdc-model-props.yml']
# readme: README text - for README.md.content
from jinja2 import Environment, FileSystemLoader
from shutil import copytree, copy
from argparse import ArgumentParser

import os
import re
import sys

ap = ArgumentParser(description="Set up a new model repo with validation and docs")
ap.add_argument('--force',
                  help="force setup despite warnings",
                  action='store_true')
ap.add_argument('mdf_files',nargs='+',
                  type=str,
                  metavar='mdf-file',
                  help='MDF files in desired merge order')

args = ap.parse_args()

# basename of repo
base = os.path.basename(os.getcwd())

has_readme = os.path.exists('README.md');
has_model_desc = os.path.isdir('./model-desc');
has_docs = os.path.isdir('./docs');

if not re.match('.*model$',base) and not args.force:
  print("The base name is '{base}', which doesn't look like a model repo.".format(base=base))
  print("Be sure you're in the top-level model repo directory")
  print("(Run script with option '--force' to force continuation)")
  if not args.force:
    sys.exit(1)

if not has_readme and not args.force:
  print("The top-level directory should contain a simple README.md.")
  print("(Run script with argument 'force' to force continuation)")
  if not args.force:
    sys.exit(1)

if not has_model_desc:
  print("The top-level directory must contain a subdir 'model-desc'.")
  print("./model-desc should contain the MDF (YAML) files.")
  sys.exit(1)

# list of MDFs
if not args.mdf_files:
  mdfs = [x for x in os.listdir('model-desc') if re.match('.*.ya?ml$',x)]
  # heuristic - merge into the yaml with the shortest name
  mdfs.sort(key=len)
else:
  mdfs = args.mdf_files
  mdfs = [os.path.basename(x) for x in mdfs]
  for f in mdfs:
    if not os.path.exists(os.path.join('model-desc',f)):
      print("The mdf file '{file}' is not present in the model-desc directory".format(file=f))
      print("Make sure all MDFs are present there and re-run.")
      sys.exit(1)

if not len(mdfs):
  print ("There are no YAML formatted files in ./model-desc.")
  print ("Make sure the MDFs are present there and re-run.")
  sys.exit(1)

# README text
readme = open("README.md").read()
print( "Setting up bento-mdf in"+os.getcwd() )

if not has_docs:
  print("Creating subdir ./docs")
  os.mkdir('./docs')

jenv = Environment(
  loader=FileSystemLoader('bento-mdf/setup/templates')
  )
  
print("Populating ./docs")
try:
  if not os.path.exists('./docs/_config.yml'):
    copy('./bento-mdf/setup/_config.yml','./docs/_config.yml')
  else:
    raise FileExistsError;
  copytree('./bento-mdf/setup/assets', './docs/assets')
except FileExistsError:
  if args.force:
    copy('./bento-mdf/setup/_config.yml','./docs/_config.yml')
    copy('./bento-mdf/setup/assets/actions.js','./docs/assets/actions.js')
    copy('./bento-mdf/setup/assets/style.css','./docs/assets/style.css')    
  else:
    print("- Not overwriting existing files.")
    print("- Remove ./docs subdir and re-run script to refresh.")

readme_content = open('./docs/README.md.content','w')
print(jenv.get_template('README.md.content.jinja').render(base=base,readme=readme),
        file=readme_content)

try:
  print("Creating docs/model-desc")
  os.mkdir('./docs/model-desc');
  os.mkdir('./docs/model-desc/diff-xls');
  open('./docs/model-desc/diff-xls/HERE','w').close()
except FileExistsError:
  pass # ignore
except Exception as e:
  raise e

if not os.path.exists('./docs/model-desc/index.html') or args.force:
  mdindex = open('./docs/model-desc/index.html','w')
  print(jenv.get_template('model-desc-index.html.jinja').render(base=base,mdfs=mdfs),
            file=mdindex)
else:
  print("- Not overwriting existing model-desc/index.html file")
  print("- Rerun with --force to overwrite")
  

print("Creating .travis.yml")
if not os.path.exists('./.travis.yml') or args.force:
    travis = open('./.travis.yml','w')
    print(jenv.get_template('travis.yml.jinja').render(base=base,mdfs=mdfs),
            file=travis)
else:
  print("- Not overwriting existing .travis.yml file")
  print("- Rerun with --force to overwrite")

print("Complete.")
