# tuf_manifest

This package provided authenticated delivery of files using manifest
files for specifying what to deliver.

Each manifest file version is numbered sequentially from 1.  The
target will keep track of the last manifest file transferred (using 1
for the initial version).  When it checks the repository, it will
attempt to transfer new manifest files by version number until it
finds the last one.  The target will then compare it to it's last
manifest file.  It will transfer any new or updated files, create
a list of new, updated, and deleted files, and transfer that to
another tool to do the actual updating.

The manifest file will be a file that is list of names and versions
and filenames, one set on each line.
