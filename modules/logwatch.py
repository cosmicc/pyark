#!/usr/bin/env python

"""
Real-time log files watcher supporting log rotation.
Works with Python >= 2.6 and >= 3.2, on both POSIX and Windows.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

import os
import time
import errno
import stat
import copy
import regex
import pickle
import logging
import binascii
import portalocker
import codecs, locale

SIG_SZ = 64

log = logging.getLogger("watcher")


class FileTooSmallToGetSignature(Exception):
    pass


class LogWatcher(object):
    """Looks for changes in all files of a directory.
    This is useful for watching log file changes in real-time.
    It also supports files rotation.

    Example:

    >>> def callback(filename, lines):
    ...     print(filename, lines)
    ...
    >>> lw = LogWatcher("/var/log/", callback)
    >>> lw.loop()
    """

    def __init__(self, folder, callback, extensions=["log"], file_path=None, tail_lines=0,
                 sizehint=1048576, persistent_checkpoint=False, file_signature_bytes=SIG_SZ):
        """Arguments:

        (str) @folder:
            the folder to watch

        (callable) @callback:
            a function which is called every time one of the file being
            watched is updated;
            this is called with "filename" and "lines" arguments.

        (list) @extensions:
            only watch files with these extensions

        (str) @file_path:
            path to a single file. If supplied the @folder arg is ignored and LogWatcher monitors only this single file

        (int) @tail_lines:
            read last N lines from files being watched before starting

        (int) @sizehint: passed to file.readlines(), represents an
            approximation of the maximum number of bytes to read from
            a file on every ieration (as opposed to load the entire
            file in memory until EOF is reached). Defaults to 1MB.
        """
        self.folder = os.path.realpath(folder)
        self.extensions = extensions
        self._single_file_path = file_path
        self._watched_files_map = {}
        self._checkpoint_files_map = {}
        self._callback = callback
        self._sizehint = sizehint
        self._init_checkpoint = ('', 0, 0)  # signature, file_modification_time, last_read_offset
        self._persistent_checkpoint = persistent_checkpoint
        self._volatile_checkpoints = dict()
        self._file_signature_size = file_signature_bytes
        log.info("Started")
        log.info("folder: %s" % self.folder)
        log.info("extensions: %s" % self.extensions)
        if self.is_single_file_mode:
            assert os.path.isdir(self.folder), self.folder
        assert callable(callback), repr(callback)
        self.update_files()
        self.update_checkpoints_to_point_to_end_of_files()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    @property
    def is_single_file_mode(self):
        if self._single_file_path is None:
            return False
        return True

    def update_checkpoints_to_point_to_end_of_files(self):
        for id, file in self._watched_files_map.items():
            log.debug("updated checkpoint to point to end of file %s" % file.name)
            with self.open(str(file.name)) as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                f.seek(os.path.getsize(file.name))  # EOF
                end_offset = f.tell()
                self.save_checkpoint(file.name, self.get_checkpoint_tuple(file.name, 0, end_offset))

    def get_checkpoint_tuple(self, fname, mtime=0, offset=0):
        signature = self.make_sig(fname)
        out_tuple = (signature, mtime, offset)
        return out_tuple

    @staticmethod
    def slugify(value):
        """
        Parameters
        ----------
        value: str
            the value to slug
        Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.
        """
        value = regex.sub('[^\w\s-]', '', value).strip().lower()
        return regex.sub('[-\s]+', '-', value)

    def load_checkpoint(self, fname):
        checkpoint_filename = self.make_checkpoint_path_from_fname(fname)

        if self._persistent_checkpoint:
            try:
                sig, mtime, offset = pickle.load(open(checkpoint_filename, 'rb'))
                log.debug('loaded: %s %s', checkpoint_filename, (sig, mtime, offset))
                return sig, mtime, offset
            except (IOError, EOFError):
                log.info('failed to load: %s; returning default checkpoint: %s' % (fname, self.get_checkpoint_tuple(fname)))
                # return self._init_checkpoint
                return self.get_checkpoint_tuple(fname)

        try:
            return pickle.loads(self._volatile_checkpoints[checkpoint_filename])
        except KeyError:
            log.info("returning default checkpoint value")
            return self._init_checkpoint

    def save_checkpoint(self, fname, checkpoint):
        checkpoint_filename = self.make_checkpoint_path_from_fname(fname)
        log.debug('dumping %s %s', checkpoint_filename, checkpoint)
        if self._persistent_checkpoint:
            return pickle.dump(checkpoint, open(checkpoint_filename, 'wb'))

        self._volatile_checkpoints[checkpoint_filename] = pickle.dumps(checkpoint)
        return True

    def delete_checkpoint_file(self, fname):
        checkpoint_filename = self.make_checkpoint_path_from_fname(fname)
        if self._persistent_checkpoint:
            try:
                os.unlink(checkpoint_filename)
                return
            except:
                log.info("could not delete checkpoint file for: %s" % fname)
        try:
            del self._volatile_checkpoints[checkpoint_filename]
        except KeyError:
            log.warning("could not delete volatile checkpoint definition for key: %s" % checkpoint_filename)

    def make_checkpoint_path_from_fname(self, fname):
        return self.slugify(fname) + ".checkpoint"

    def loop(self, interval=0.1, blocking=True):
        """Start a busy loop checking for file changes every *interval*
        seconds. If *blocking* is False make one loop then return.
        """
        # May be overridden in order to use pyinotify lib and block
        # until the directory being watched is updated.
        # Note that directly calling readlines() as we do is faster
        # than first checking file's last modification times.
        while True:
            self.update_files()
            for fid, file in list(self._watched_files_map.items()):
                log.debug("reading lines from %s" % file.name)
                self.readlines_from_checkpoint(file)
                # self.readlines(file)
            if not blocking:
                return
            time.sleep(interval)

    def log(self, line):
        """Log when a file is un/watched"""
        print(line)

    def listdir(self):
        """List directory and filter files by extension.
        You may want to override this to add extra logic or globbing
        support.
        """
        if self.is_single_file_mode:
            if os.path.isfile(self._single_file_path):
                return [self._single_file_path]
            log.error("provided single file path does not point to a file: %s" % self._single_file_path)
            return []

        ls = os.listdir(self.folder)
        log.debug(ls)
        log.debug([os.path.splitext(x)[1][1:] for x in ls])
        if self.extensions:
            return [x for x in ls if os.path.splitext(x)[1][1:] in self.extensions]
        else:
            return ls

    @classmethod
    def open(cls, file_path):
        """Wrapper around open().
        By default files are opened in binary mode and readlines()
        will return bytes on both Python 2 and 3.
        This means callback() will deal with a list of bytes.
        Can be overridden in order to deal with unicode strings
        instead, like this:
        """
        return codecs.open(file_path, 'r', encoding=locale.getpreferredencoding(), errors='ignore')
        # return open(file_path, 'rb+')

    @classmethod
    def tail(cls, fname, window):
        """Read last N lines from file fname."""
        if window <= 0:
            raise ValueError('invalid window value %r' % window)
        with cls.open(fname) as f:
            f.seek(os.path.getsize(f.name))  # EOF
            BUFSIZ = 1024
            # True if open() was overridden and file was opened in text
            # mode. In that case readlines() will return unicode strings
            # instead of bytes.
            encoded = getattr(f, 'encoding', False)
            CR = '\n' if encoded else b'\n'
            data = '' if encoded else b''
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            block = -1
            exit = False
            while not exit:
                step = (block * BUFSIZ)
                if abs(step) >= fsize:
                    f.seek(0)
                    newdata = f.read(BUFSIZ - (abs(step) - fsize))
                    exit = True
                else:
                    f.seek(step, os.SEEK_END)
                    newdata = f.read(BUFSIZ)
                data = newdata + data
                if data.count(CR) >= window:
                    break
                else:
                    block -= 1
            return data.splitlines()[-window:]

    def update_files(self):
        ls = []
        for name in self.listdir():
            absname = os.path.realpath(os.path.join(self.folder, name))
            log.debug("found matching file: %s" % absname)
            try:
                st = os.stat(absname)
            except EnvironmentError as err:
                if err.errno != errno.ENOENT:
                    raise
            else:  # no error occurred
                if not stat.S_ISREG(st.st_mode):
                    continue
                for tries_count in range(3):
                    try:
                        fid = self.get_file_id(absname)
                        log.debug("got possibly new file: %s" % absname)
                        ls.append((fid, absname))
                        break
                    except (IOError, WindowsError):
                        log.warning("had to repeat getting file ID while adding to list of files to watch")
                        time.sleep(0.1)
                    except FileTooSmallToGetSignature:
                        log.warning("file too small to calculate signature: %s" % absname)

        # check existent files
        for fid, file in list(self._watched_files_map.items()):
            try:
                st = os.stat(file.name)
            except EnvironmentError as err:
                if err.errno == errno.ENOENT:
                    log.debug("unwatching file: %s" % file)
                    self.unwatch(file, fid)
                else:
                    raise
            else:  # no error occurred
                try:
                    if fid != self.get_file_id(file.name):
                        # same name but different file (rotation); reload it.
                        log.info("reloading file due to rotation: %s" % file.name)
                        self.unwatch(file, fid)
                        self.watch(file.name)
                except FileTooSmallToGetSignature:
                    log.warning("file too small to re-watch it; will just unwatch")
                    self.unwatch(file, fid)
                except (IOError, WindowsError):
                    log.exception("file access error; will just unwatch")
                    self.unwatch(file, fid)

        # add new ones
        for fid, fname in ls:
            log.debug("checking if file is not added to _files_map: %s, fid: %s" % (fname, fid))
            log.debug("already added files: %s" % str(self._watched_files_map.keys()))
            if fid not in self._watched_files_map:
                log.debug("adding new file to watch: %s" % fname)
                try:
                    self.watch(fname)
                except (IOError, WindowsError):
                    log.exception("file access error; will not add new file to watch")
                except FileTooSmallToGetSignature:
                    log.exception("file too small to be added for watching")

        log.debug("self._files_map after update: %s" % str(self._watched_files_map))

    def readlines_from_checkpoint(self, file, checkpoint=None, overloaded_file_name=None):
        """Read file lines since last access until EOF is reached and
        invoke callback.
        """
        try:
            log.debug(">> loading checkpoint")
            if checkpoint is None:
                sig, mtime, offset = self.load_checkpoint(file.name)
            else:
                log.debug(" > used provided kwarg value")
                sig = list(checkpoint)[0]
                mtime = list(checkpoint)[1]
                offset = list(checkpoint)[2]

            log.debug("<< loading checkpoint")

            out_offset = copy.copy(offset)
            log.debug("starting offset: %s" % offset)
            try:
                buff = []
                lines_read = False
                with self.open(file.name) as f:
                    portalocker.lock(f, portalocker.LOCK_SH)
                    f.seek(os.path.getsize(file.name))
                    file_size = f.tell()
                    if offset > file_size:
                        log.error("file smaller than last offset; POSSIBLE DATA LOSS - ARE LOGS POLLED FREQUENTLY ENOUGH?")
                        log.debug("offset: %s" % offset)
                        log.debug("tell: %s" % file_size)
                        offset = 0
                        out_offset = 0

                    log.debug("seek to offset: %s" % offset)
                    f.seek(offset)

                    while True:
                        line = f.readline()
                        if not line:
                            break
                        buff.append(line.decode('utf-8'))
                        out_offset += len(line)

                    if out_offset != offset:

                        if buff[-1].strip() == "":
                            del(buff[-1])
                            out_offset -= 1
                        lines_read = True

                if lines_read:
                    self.save_checkpoint(file.name, self.get_checkpoint_tuple(file.name, offset=out_offset))
                    if overloaded_file_name is None:
                        self._callback(file.name, buff)
                    else:
                        self._callback(overloaded_file_name, buff)

            except IOError:
                log.exception("failed to read input file: %s" % file.name)
                return False
            else:  # no error in reading tail
                return len(buff)

        except ValueError:
            log.exception("could not read lines from file: %s" % file.name)
            return False

    def readlines(self, file):
        """Read file lines since last access until EOF is reached and
        invoke callback.
        """
        try:
            with self.open(file.name) as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                while True:
                    lines = f.readlines(self._sizehint)
                    if not lines:
                        break
                    self._callback(f.name, lines)
        except ValueError:
            log.exception("could not read lines from file: %s" % file.name)
            return

    def watch(self, fname):
        log.info(">> watch: %s" % fname)
        try:
            with self.open(fname) as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                fid = self.get_file_id(fname)
                self._watched_files_map[fid] = f
                self._watched_files_map[fid].close()
                log.info("watching logfile %s" % fname)
        except EnvironmentError as err:
            if err.errno != errno.ENOENT:
                raise
        except FileTooSmallToGetSignature:
            raise

    def unwatch(self, file, fid):
        # File no longer exists. If it has been renamed try to read it
        # for the last time in case we're dealing with a rotating log
        # file.
        log.info("un-watching logfile %s" % file.name)

        # last reading attempt may block log file from appending by the logger itself
        '''
        try:
            with file:
                lines = self.readlines_from_checkpoint(file)
                if lines:
                    self._callback(file.name, lines)
        except ValueError:
            pass
            #log.exception("could not make a final readlines on a possibly closed file")
        '''

        try:
            sig, mtime, offset = self.load_checkpoint(file.name)
            log.info(">> reading rotated file's tail")
            rolled_file_name = file.name + ".1"
            with self.open(rolled_file_name) as rolled_file:
                portalocker.lock(rolled_file, portalocker.LOCK_SH)
                backfilled_lines_count = 0
                # print("-->")
                if sig == self.make_sig(rolled_file_name):
                    backfilled_lines_count = self.readlines_from_checkpoint(rolled_file,
                                                                            checkpoint=(sig, mtime, offset),
                                                                            overloaded_file_name=file.name)
                else:
                    log.warning("rolled file signature doesn't match")
                    try:
                        del self._watched_files_map[fid]
                    except KeyError:
                        pass
                    return  # FIXME: checkpoint structure should keep the buffer length used to create file signature and readlines should skip non-matching checkpoint files
                # print("<--")
                if os.path.isfile(rolled_file_name):
                    self.delete_checkpoint_file(rolled_file_name)
                log.info("<< reading rotated file's tail")
        except IOError:
            pass

        del self._watched_files_map[fid]
        self.delete_checkpoint_file(file.name)

    def get_file_id(self, fname):
        st = os.stat(fname)
        file_size = os.path.getsize(fname)
        if file_size < self._file_signature_size:
            raise FileTooSmallToGetSignature
        if os.name == 'posix':
            return "%xg%x" % (st.st_dev, st.st_ino)
        else:
            return "%f_%s" % (st.st_ctime, self.make_sig(fname))

    @classmethod
    def make_sig(cls, file_to_check, stat=None):
        with cls.open(file_to_check) as fh:
            return cls.sig(fh)
            # return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()

    @classmethod
    def sig(cls, file_to_check_fh, stat=None):
        return str(binascii.crc32(file_to_check_fh.read(SIG_SZ)) & 0xffffffff)

    def close(self):
        for id, file in self._watched_files_map.items():
            file.close()
        self._watched_files_map.clear()
