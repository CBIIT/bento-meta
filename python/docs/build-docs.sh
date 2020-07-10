#!/bin/bash
REPO=../..
echo update the_object_model
python3 gen_attr_doc.py > tom.rst
mv the_object_model.rst the_object_model.rst.old
mv tom.rst the_object_model.rst
echo sphinx build
sphinx-build -b html . _build *.rst
echo move to $REPO/docs
cp -aR _build/* $REPO/docs
