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

### Delivery types

Three possible ways this can be used: package delivery, update deltas,
and full update delivery.

#### Package delivery

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

#### Full updates

For full image updates, each manifest will have one file (or a set of
files if multiple images are involved) in it: the update file(s) with
the same name(s) and a new version.  tuf-manifest will deliver the
update to the update handler.

### Setting up the repo host

The first thing you need to do is create a TUF repo.  This is not
covered here, it is a complex task whose steps depend on your security
requirements.  See the TUF documentation for that.

After you have an initial repo created, you need the tufrepo and keys
(without the root keys, of course, for best security).

You also need to create a manifest file in the form:

  <packagename> <version> <filename>

One line per package.  The filename is not the full path to the file,
just the name.  You need to have all the files someplace, too.

The manifest file put into the repository, too, so it's name is
important.  It must match what the client has set in its configuration
file, and it must end in a .<num> that is sequentially increasing from 1.
The client looks for the filename.<num> sequentially from it's current
setting, so this is important.

Once you have everything ready, run:

  gitm-repo --load-manifest --manifest <manifest file> \
      --manifest-dir <directories where the files are>

The files are loaded into the manifest.

So, for a simple example, lets say we have the following manifest file:

  a 1.0 a-1.0.pack
  a-info 1.0 a-info-1.0.txt

in $HOME/builda/manifest.1, and we have $HOME/builda/files/a-1.0.pack
and $HOME/builda/info/a-info-1.0.txt.  You would cd to the repository
and run:

  tufm-repo --load-manifest --manifest $HOME/builda/manifest.1 \
      --manifest-dir $HOME/builda/files $HOME/builda/info

and a-1.0.pack and a-info-1.0.txt will be put into the repository.

If you come out with a new version, you need to create the next
manifest file version for it, lets say:

  a 1.0 a-1.0.pack
  b 2.0 b-2.0.pack
  b-info 2.0 b-info-2.0.txt

and name it $HOME/builda/manifest.2.  Then run:

  tufm-repo --load-manifest --manifest $HOME/builda/manifest.1 \
      --manifest-dir $HOME/builda/files $HOME/builda/info

and b-2.0.pack and b-info-2.0.txt will be added.  Note that
a-info-1.0.txt will not be deleted from the repository, it's just not
in the second manifest.  When the client fetches manifest.2, it will
see that a-info is gone and b and b.info are added.

#### Maintaining timestamps in the repo

The file timestamps for the timestamp and snapshot file expire often
by default, 1 day for timestamp and 7 days for snapshots.  The
standard repo command from tuf does not have a method to update this,
so tufm-repo has added one.  Do:

  tufm-repo --update-timestamp --role <role> --expires <time>

to get a new timestamp for the given role.  --expires takes either
+<n>[dwy] for a relative day/week/year or seconds if no suffix, or an
iso8601 date.

### Setting up the target

On the client side you need some files on the filesystem for
configuration and current states.  These are the default name, the
config file can be overridden on the command line and the other
filenames can be overridden in the config file.

#### /etc/tuf-manifest.conf

The format of this file is:

    [Manifest]
    vardir=/var/tuf-manifest
    numfile=<vardir>/num
    repodir=<vardir>
    filedir=<vardir>/files
    url=<user must set this>
    filebase=manifest
    handler=<user must set this>

The only things required in the configuration file are the url of the
tuf server and the handler, which is the program that gets executed
with the new, updated, and deleted files.

For the non-required items, the default are shown above.

vardir is the base location for the tuf-manifest files.

The numfile is a file holding the current manifest number.  If
this class successfully does an update, the new manifest number will
be written into this file.

The repodir is the directory where tufrepo resides (which holds
the metadata).

The filedir is where the files (inlcuding the manifests) are
downloaded to.  Note that after the handler finishes its execution,
it is free to delete all the files in this directory, though leaving
the manifests around will speed things up a little bit.

filebase sets the manifest filename (without the ".<number>"
appended).  You can change the manifest filename for clarity, and to
allow multiple release streams for different things to be held in the
same repository.

The handler is a program that will receive the list of files.  The
first argument is a space-seperated list of new files (full path), the
second is a space-separated list of updated files (full path), and the
third is a space-separated list of package names (no filename or path)
that were deleted.  If the handler returns success, this class will
assume the update is successful and update to the new manifest number.
If it returns failure, it will leave the manifest number alone.

#### /var/tuf-manifest/num

Holds the current manifest number installed.  It is a python config
file format, like:

    [Manifest]
    curr_manifest=<n>

It is updated when new manifests are installed.

#### /var/tuf-manifest/tufrepo

This is the tufrepo dir from the tufclient directory where the repo is
created.  It holds the client metadata and is updated with new
metadata as that becomes available.

#### /var/tuf-manifest/files

This is where the files are downloeded to.

### Target operation

On the target, just periodically run "tufm-client" and it will do the
rest.  You should log the output of this command and any subcommands
and report an issue if it return an error.