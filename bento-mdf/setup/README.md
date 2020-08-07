# Setting up a new model repository

This directory contains a script, [new-repo-setup.py](./new-repo-setup.py), that will
instrument a new Bento-based model repository for automatic [travis](https://travis-ci.org) validation and [GitHub Pages](https://pages.github.com/) setup. More details are found in the work process document in Teams.

Briefly, to use the script:

* Pull the model repo to a working directory on your machine. ``cd`` to the top level.

        git clone https://github.com/<my_new_model>.git
        cd <my_new_model>

* The model repo should contain bento-mdf as a git submodule. 
  * If no ``bento-mdf`` directory exists, create the submodule as follows

        git submodule add https://github.com/CBIIT/bento-mdf

  * If the ``bento-mdf`` directory is empty, run the following commands

        git submodule init
        git submodule update

* Get the necessary python modules with pip

        pip install -r ./bento-mdf/setup/requirements.txt

* Insure the model definition files (YAMLs) are present in a subdirectory called ``model-desc``

* Run the ``new-repo-setup.py`` script as follows:

        python bento-mdf/setup/new-repo-setup <my_new_model>.yaml <my_new_model>-properties.yaml

* READ the output to make sure everything worked. If not, follow the script's instructions.

* Commit and push all the changes made by the script.

        git add .
        git commit -m 'bento-mdf setup for model'
        git push

Other steps are required to get Travis working. See the work process document.

