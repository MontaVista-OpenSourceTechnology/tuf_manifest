#!/usr/bin/env python

# Copyright 2019, MontaVista Software, LLC
# SPDX-License-Identifier: MIT

import tuf
import tuf.scripts.repo
import tuf.formats
import tuf.roledb
import tuf.repository_tool as repo_tool
import time
import datetime
import iso8601
import os
import os.path
import shutil

year_seconds = 31556900
week_seconds = 604800
day_seconds = 86400

def get_expiry(arguments):
    expires = arguments.expires
    if expires.startswith('+'):
        # It's a relative time.
        if expires.endswith('d'):
            expires = int(expires[1:-1]) * day_seconds
        elif expires.endswith('w'):
            expires = int(expires[1:-1]) * week_seconds
        elif expires.endswith('y'):
            expires = int(expires[1:-1]) * year_seconds
        else:
            expires = int(expires[1:])
        expires = int(expires + time.time())
        expires = tuf.formats.unix_timestamp_to_datetime(expires)
    else:
        expires = iso8601.parse_date(expires)
    return expires

def get_arg_repo_role(repo, arguments):
    if (arguments.role == "root"):
        role = repo.root
    elif (arguments.role == "targets"):
        role = repo.targets
    elif (arguments.role == "snapshot"):
        role = repo.snapshot
    elif (arguments.role == "timestamp"):
        role = repo.timestamp
    else:
        role = repo.targets(arguments.role)

    return role

def get_role_privatekey(role, arguments):
    return os.path.join(arguments.path, tuf.scripts.repo.KEYSTORE_DIR,
                        role.rolename + "_key")

def update_timestamp(arguments):
    expires = get_expiry(arguments)

    repo = repo_tool.load_repository(
        os.path.join(arguments.path, tuf.scripts.repo.REPO_DIR))

    role = get_arg_repo_role(repo, arguments)

    role.expiration = expires

    repo.mark_dirty([arguments.role])

    if arguments.sign is not None:
        keypath = arguments.sign
    else:
        keypath = get_role_privatekey(role, arguments)

    role_privatekey = tuf.scripts.repo.import_privatekey_from_file(keypath,
                                                                   arguments.pw)
    role.load_signing_key(role_privatekey)

    consistent_snapshot = tuf.roledb.get_roleinfo('root',
        repo._repository_name)['consistent_snapshot']
    repo.writeall(consistent_snapshot=consistent_snapshot)
    tuf.scripts.repo.write_to_live_repo(arguments)
    return

def load_manifest(manifest, dirs, arguments):
    rpath = os.path.join(arguments.path, tuf.scripts.repo.REPO_DIR)
    tpath = os.path.join(rpath, "targets")
    manifest_base = os.path.basename(manifest)
    if os.path.exists(os.path.join(tpath, manifest_base)):
        tuf.exceptions.Error("Manifest %s already exists" % manifest)

    files = [manifest_base]
    with open(manifest) as infile:
        lineno = 1
        for line in infile:
            if line[0] != '#':
                try:
                    (name, ver, filename) = line.split()
                except:
                    tuf.exceptions.Error("Invalid manifest on line %s" % lineno)
                found = False
                for d in dirs:
                    sfname = os.path.join(d, filename)
                    if os.path.isfile(sfname):
                        dfname = os.path.join(tpath, filename)
                        if not os.path.exists(dfname):
                            shutil.copyfile(sfname, dfname)
                            files.append(filename)
                        found = True
                        break
                if not found:
                    tuf.exceptions.Error("Manifest has file %s on line %s, "
                                         "but it does not exist" %
                                         (filename, lineno))

            lineno += 1

        shutil.copyfile(manifest, os.path.join(tpath, manifest_base))
    return files

def load_manifests(arguments):
    repo = repo_tool.load_repository(os.path.join(arguments.path,
                                                  tuf.scripts.repo.REPO_DIR))
    if not arguments.manifest_dir:
        dirs = [ os.getcwd() ]
    else:
        dirs = arguments.manifest_dir

    if not arguments.manifest:
        tuf.exceptions.Error("--Manifest must be specified with "
                             "--load-manifest")
    roleinfo = tuf.roledb.get_roleinfo(arguments.role,
                                       repository_name=repo._repository_name)
    newfiles = []
    for manifest in arguments.manifest:
        newfiles += load_manifest(manifest, dirs, arguments)
    for filename in newfiles:
        roleinfo['paths'].update({filename: {}})
    tuf.roledb.update_roleinfo(arguments.role, roleinfo,
                               mark_role_as_dirty=True,
                               repository_name=repo._repository_name)

    tuf.scripts.repo.write_updated_targets(arguments, repo)
    return

def create_argument_parser():
    parser = tuf.scripts.repo.create_argument_parser()

    parser.add_argument('--update-timestamp', action='store_true',
        help="Update the timestamp for the given role's metadata.  Uses "
             "--expires for the expiry time, also takes --sign to specify "
             "a different key and --pw for the password")

    parser.add_argument('--expires', default="+1d",
        help="Expiry time, like for --update-timestamp."
             " Either +<n>[dwy] for a relative day/week/year or"
             " seconds if no suffix, or an iso8601 date.")

    parser.add_argument('--load-manifest', action='store_true',
        help="Load files from a manifest into the repository. The manifests() "
             "to load are specified by --manifest, you must supply "
             "at least one.  Files in the manifest will be copied "
             "to the repository if they are not already there. "
             "By default files come from the current directory. "
             "You can use --manifest-dir to add one or more directories "
             "that files will be loaded from.")

    parser.add_argument('--manifest', type=str, nargs='+',
        metavar='</path/to/manifest>',
        help="The manifest file(s) to use with --load-manifest")

    parser.add_argument('--manifest-dir', type=str, nargs='+',
        metavar='</path/to/directory>',
        help="The manifest directories(s) to use with --load-manifest")

    return parser

def process_arguments(arguments):
    if arguments.update_timestamp:
        update_timestamp(arguments)
    if arguments.load_manifest:
        load_manifests(arguments)
    tuf.scripts.repo.process_arguments(arguments)
    return

def parse_arguments():
    parser = create_argument_parser()

    parsed_args = parser.parse_args()

    tuf.scripts.repo.process_log_arguments(parsed_args)

    return parsed_args
