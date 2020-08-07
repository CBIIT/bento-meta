import pytest
from yaml.parser import ParserError
from yaml.constructor import ConstructorError
from jsonschema import ValidationError, SchemaError, RefResolutionError
from MDFValidate.validator import MDFValidator

test_schema_file = 'samples/mdf-schema.yaml'
test_mdf_files = ['samples/ctdc_model_file.yaml','samples/ctdc_model_properties_file.yaml']
test_schema_bad = 'samples/mdf-bad-schema.yaml'
test_yaml_bad = 'samples/ctdc_model_bad.yaml'
test_yaml_with_keydup = 'samples/ctdc_model_keydup.yaml'
test_mdf_files_invalid_wrt_schema = ['samples/ctdc_model_file_invalid.yaml','samples/ctdc_model_properties_file.yaml']

def test_with_all_File_args():
  sch = open(test_schema_file,"r")
  mdf0 = open(test_mdf_files[0],"r")
  mdf1 = open(test_mdf_files[1],"r")  
  assert MDFValidator(sch, mdf0, mdf1)
    
def test_with_all_str_args():
  assert MDFValidator(test_schema_file, *test_mdf_files)

def test_with_remote_schema():
  v = MDFValidator(None, *test_mdf_files)
  assert v
  assert v.load_and_validate_schema()
  assert v.load_and_validate_yaml()

def test_bad_yaml():
  v = MDFValidator(test_schema_file, test_yaml_bad)
  with pytest.raises(ParserError):
    v.load_and_validate_yaml()

def test_keydup_yaml():
  v = MDFValidator(test_schema_file, test_yaml_with_keydup)
  with pytest.raises(ConstructorError):
    v.load_and_validate_yaml()

def test_bad_schema():
  pytest.skip()
  v =  MDFValidator(test_schema_bad, *test_mdf_files)
  with pytest.raises(SchemaError):
    v.load_and_validate_schema()
   
def test_instance_not_valid_wrt_schema():
  v =  MDFValidator(test_schema_file, *test_mdf_files_invalid_wrt_schema)  
  assert v.load_and_validate_schema()
  assert v.load_and_validate_yaml()
  with pytest.raises(ValidationError):
    v.validate_instance_with_schema()
  
  

  



