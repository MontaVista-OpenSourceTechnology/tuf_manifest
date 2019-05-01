#!/usr/bin/env python

# Copyright 2019, MontaVista Software, LLC
# SPDX-License-Identifier: MIT

"""
This file contains a class for pulling updates from a remote
server using The Update Framework (tuf) based upon manifest files.
See the tuf_manifest_client class below for details.
"""

import os.path
import ConfigParser
import logging
import subprocess
import sys

import tuf
import tuf.client.updater
import tuf.settings
import tuf.log

logger = logging.getLogger('tuf.scripts.client')

default_conffile = os.path.join("etc", "tuf-manifest.conf")
default_vardir = os.path.join("var", "tuf-manifest")

confdefaults = {
    'vardir'  :  default_vardir,
    'numfile' : None,
    'filedir' : None,
    'url'     : None,
    'filebase': None,
    'handler' : None
}

def read_manifest(filename):
    """A manifest file has one file information on each line.  The file
    information consists of three items: A name, a version, and a
    filename.  The name should be unique and should be kept the same
    between manifest files.  The version should be updated if the file
    changes.  The filename is the file to fetch from the tuf server.

    This function returns a dictionary indexed by the name.  Each
    dictionary contains a list with the version string first and the
    filename second.
    """
    mf = {}
    with open(filename) as f:
        lineno = 1;
        for line in f:
            v = line.split()
            if len(v) != 3:
                logger.error("Invalid manifest file '%s', line %d invalid" %
                             (filename, lineno))
            mf[v[0]] = v[1:]
            lineno = lineno + 1
    return mf

class tuf_manifest_client:
    """This class uses manifest files on a tuf server to process updates.
    On allocation is reads a configuration file and sets things up.  The
    configuration file is in /etc/tuf-manifest.conf by default, but
    a different one may be passed into the init function.

    The configuration file looks like:

    [Manifest]
    vardir=/var/tuf-manifest
    numfile=<vardir>/num
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
    be written into this file.  It is a python config file format, like:
    [Manifest]
    curr_manifest=n

    The filedir is where the files (inlcuding the manifests) are
    downloaded to.  Note that after the handler finishes its execution,
    it is free to delete all the files in this directory.

    The handler is a program that will receive the list of files.  The
    first argument is a space-seperated list of new files, the second
    is a space-separated list of updated files, and the this is a
    space-separated list of files that were deleted.  If the handler
    returns success, this class will assume the update is successful
    and update to the new manifest.  If it returns failure, it will
    leave the manifest number alone.

    Call the do_update() method to actually perform the operation.
    """

    def __init__(self, conffile = None, vardir = None, numfile = None,
                 url = None, filedir = None, filebase = None, handler = None):
        """Allocate a new object.  All the configuration items may be
        overridden by passing in strings for them.
        """
        if conffile is None:
            conffile = default_conffile;
        config = ConfigParser.ConfigParser()
        config.read((conffile))
        if vardir is None:
            vardir = config.get("Manifest", "vardir")
        if numfile is None:
            numfile = config.get("Manifest", "numfile")
            if numfile is None:
                numfile = os.path.join(vardir, "num")
        if url is None:
            url = config.get("Manifest", "url")
            if url is None:
                raise Exception("No url in config file %s" % conffile)
        if filedir is None:
            filedir = config.get("Manifest", "filedir")
            if filedir is None:
                filedir = os.path.join(vardir, "files")
        if filebase is None:
            filebase = config.get("Manifest", "filebase")
            if filebase is None:
                filebase = "manifest"
        if handler is None:
            handler = config.get("Manifest", "handler")
            if handler is None:
                raise Exception("No handler in config file %s" % conffile)
            
        self.vardir = vardir
        self.numfile = numfile
        self.url = url
        self.filedir = filedir
        self.filebase = filebase
        self.handler = handler

        numconfig = ConfigParser.ConfigParser({ "curr_manifest" : "1" })
        numconfig.read((self.numfile))
        self.curr_num = numconfig.getint("Manifest", "curr_manifest")
        return

    def get_manifest(self, num = 0):
        if num == 0:
            num = self.curr_num

        mff = self.filebase + '.' + str(self.curr_num)
        mff_full = os.path.isfile(os.path.join(self.filedir, mff))
        target = get_one_valid_target(mff)
        updated_target = update.updated_targets((target), self.filedir)
        for target in updated_target:
            updater.download_target(target, self.filedir)

        return mff_full

    def get_files(self, file_list):
        updated_targets = update.updated_targets(file_list, self.filedir)
        for target in updated_target:
            try:
                updater.download_target(target, self.filedir)
            except tuf.exceptions.DownloadError:
                logger.error("Unable to download file '%s'" % target)
                raise
        return

    def process_new_manifest(self, curr_mff, new_mff):
        curr_mf = read_manifest(curr_mff)
        new_mf = read_manifest(new_mff)
        new = []
        updated = []
        deleted = []
        for i in curr_mf:
            if i in new_mf:
                if curr_mf[i][0] != new_mf[i][0]:
                    # Version updated
                    updated.append(new_mf[i][1])
                del curr_mf[i]
                del new_mf[i]
            else:
                deleted.append(curr_mf[i][1])
                del curr_mf[i]
        for i in new_mf:
            new.append(new_mf[i][1])
        self.get_files(updated + new)
        return subprocess.call((self.handler, " ".join(new),
                                " ",join(updated), " ".join(deleted)))

    def do_update(self):
        """When the do_update() method is called it will connect to the
        remote server and look for new manifests.  If it finds new
        manifests, it will find the newest one.  Then it will compare
        that with the last used manifest file.

        Based on that comparison, it will create a list of new, updated,
        and deleted files.  It will transfer the new and updated files
        from the tuf server and then call a handler program with each
        list of files.

        This method returns 0 if successful or the error return code
        from the handler program if not.
        """
        repository_mirrors = {'mirror': {'url_prefix': self.url,
                                         'metadata_path': 'metadata',
                                         'targets_path': 'targets',
                                         'confined_target_dirs': ['']}}

        updater = tuf.client.updater.Updater('tufrepo', repository_mirrors)

        updater.refresh(unsafely_update_root_if_necessary=False)

        # Get the current manifest if we do not already have it.
        try:
            curr_mff = self.get_manifest()
        except tuf.exceptions.DownloadError:
            logger.error("Unable to download current manifest")
            raise

        # Now try to get manifest files until we can't get one.
        i = self.curr_num + 1
        new_mff = None
        while True:
            try:
                new_mff = self.get_manifest(i)
            except tuf.exceptions.DownloadError:
                break
            i = i + 1
        if new_mff is None:
            # No new manifest file, just quit.
            return

        i = i - 1
        rv = self.process_new_manifest(curr_mff, new_mff)

        if rv == 0:
            # Update was successfull, save the new manifest file number
            numconfig = ConfigParser.ConfigParser()
            numconfig.set("Manifest", "curr_manifest", str(i))
            numconfig.write(open(self.numfile))

            # Remove all the old manifest files.
            for j in range(self.curr_num, i - 1):
                os.remove(os.path.join(self.filedir,
                                       self.filebase + "." + str(j)))
        return rv

if __name__ == '__main__':
    c = tuf_manifest_client()
    sys.exit(c.do_update())
