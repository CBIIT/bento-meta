import sys
sys.path.insert(0, '..')
import os
import getpass
import argparse
from bento_meta.mdf import MDF
from bento_meta.mdb import MDB, make_nanoid

parser = argparse.ArgumentParser(description="Load model in MDF into an MDB")
parser.add_argument('files', nargs="*",
                    metavar="MDF-FILE", help="MDF file(s)/url(s)")
parser.add_argument('--commit', default='',
                    help="commit SHA1 for MDF instance (if any)",
                    required=True)
parser.add_argument('--handle', help="model handle")
parser.add_argument('--user', help="MDB username")
parser.add_argument('--passw', help="MDB pass")
parser.add_argument('--bolt', metavar="BoltURL", help="MDB Bolt url endpoint")
parser.add_argument('--put', action='store_true')
# args = parser.parse_args([
#     "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/master/model-desc/icdc-model.yml",
#     "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/master/model-desc/icdc-model-props.yml",
#     "--commit",
#     "a4aa9a43b9ad2087638ceaeef50d4a22a4b9b959",
#     "--handle",
#     "ICDC",
#     "--bolt",
#     "bolt://localhost:7687",
#     "--user",
#     "neo4j",
#     "--passw",
#     getpass.getpass()
#     ])

args = parser.parse_args()

if not args.files:
    parser.print_help()
    parser.exit(1)

if args.put and not args.passw:
    args.passw = getpass.getpass()

print("load model from MDFs")
mdf = MDF(*args.files, handle=args.handle, _commit=args.commit)
model = mdf.model
if (args.bolt):
    mdb = MDB(uri=args.bolt, user=args.user, password=args.passw)
    model.mdb = mdb

if args.put:
    print("Put model to DB")
    model.dput()
    print("Add nanoids to nodes")
    with mdb.driver.session() as s:
        result = s.run(
            "match (n {_commit:$commit}) where not exists(n.nanoid) "
            "with n limit 1 set n.nanoid=$nanoid return n",
            {"commit":args.commit, "nanoid":make_nanoid()}
            )
        while (result.peek()):
            result = s.run(
                "match (n {_commit:$commit}) where not exists(n.nanoid) "
                "with n limit 1 set n.nanoid=$nanoid return n",
                {"commit":args.commit, "nanoid":make_nanoid()}
                )
