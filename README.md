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

## How to use this

This code should make it easier to handle delivery of update content
using tuf.  tuf itself is not an updater, it is an authenticated file
transfer mechanism.  This code takes it a step closer to being an
update mechanism by automatically transferring files required for an
update and calling a program with those file names and whether they
are new or need to be updated.  It also supplies names that have been
deleted.

Three possible ways this can be used: package delivery, update deltas,
and full update delivery.

### Package delivery

For updates involving a package management system like RPM or dpkg,
each manifest file will contain all the packages to be installed on
the target for that version.  When a new manifest file comes out, the
update handler program will be called by tuf-manifest will packages to
be added, updated, and deleted.  These files will already be
downloaded and ready, it's just a matter of applying them.

The difficulty here comes in the manifest management.  But build
systems like yocto can automatically generate these types of manifests
from the build.

For atomicity, something like rpm-ostree can make the updates install
atomically to avoid issues with reboots or shutdowns during an update.

#### Update deltas

For updates that involve a blob being applied to be appended to an
existing install, like an ostree binary or clear linux update, each
manifest will have all the previous installs plus the new update
appended to the end.  tuf-manifest will call the update handler with
all the new updates to be installed, already downloaded and ready.

### Full updates

For full image updates, each manifest will have one file (or a set of
files if multiple images are involved) in it: the update file(s) with
the same name(s) and a new version.  tuf-manifest will deliver the
update to the update handler.