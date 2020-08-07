#!/usr/bin/env python 
#from pdb import set_trace
from sys import exit
from argparse import ArgumentParser, FileType
import requests

from MDFValidate.validator import MDFValidator

ap = ArgumentParser(description="Validate MDF against JSONSchema")
ap.add_argument('--schema',
                  help="MDF JSONschema file", type=FileType('r'),
                  dest="schema")
ap.add_argument('mdf_files',nargs='+',
                  metavar='mdf-file',
                  type=FileType('r'),
                  help="MDF yaml files for validation")


def test(v):
  retval = 0
  try:
    v.load_and_validate_schema()
  except:
    retval+=1;
    pass
  try:
    v.load_and_validate_yaml()
  except:
    retval+=1;
    pass
  try:
    v.validate_instance_with_schema()
  except:
    retval+=1;
    pass
  return retval

if __name__ == '__main__':
  args = ap.parse_args()
  v = MDFValidator( args.schema,*args.mdf_files )
  exit(test(v)) # emit return val (0 = good) to os

