#! /usr/bin/env python

"""
a linter for build systems composed of bunches of FAKE .fsx scripts that like to #load each other.

this probably has a pretty small target audience. hello!
"""

import os
import os.path
import fnmatch
import re
from collections import namedtuple, defaultdict
import logging as _logging
import sys
import argparse


Dep = namedtuple('Dep', ['src', 'dst', 'debug_file_name', 'debug_line_number'])
Target = namedtuple('Target', ['type', 'name'])


def make_logger():
    logger = _logging.getLogger('build_lint')
    handler = _logging.StreamHandler()
    formatter = _logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger



def pop_elements(p, xs):
    for i in reversed(xrange(len(xs))):
        if p(xs[i]):
            xs.pop(i)
    return xs


def find(root_path, pattern, dir_exclude_pattern='.*'):
    for root, dd, ff in os.walk(root_path):
        for f in ff:
            if fnmatch.fnmatch(f, pattern):
                yield os.path.join(root, f)
        if dir_exclude_pattern is not None:
            pop_elements((lambda x : fnmatch.fnmatch(x, dir_exclude_pattern)), dd)



def gen_matching_lines(regex, lines):
    for i, line in enumerate(lines, start=1):
        match = re.search(regex, line)
        if match is None:
            continue
        yield i, list(match.groups())


def find_fsx_load_dependencies(fsx_file):
    z = re.compile(r'[ \t]*#load[ \t]+"([^"\r\n]+)"')
    with open(fsx_file, 'r') as f:
        for i, xx in gen_matching_lines(z, f):
            assert len(xx) == 1 # assume only one '#load' per line
            yield i, xx[0]


def find_build_target_defns(fsx_file):
    """
    match things of form
    [prefix]Target "name"
    """
    #this will only be approximate, unless we actually parse+run fsharp code
    z = re.compile(r'([\w]*Target)[ \t]+"([^"\r\n]+)"')
    with open(fsx_file, 'r') as f:
        for i, xx in gen_matching_lines(z, f):
            assert len(xx) == 2 # should have (TargetType, TargetName)
            target_type, target_name = xx
            if target_type == 'ActivateFinalTarget': # HACK - this isnt a target, it is a function acting on a previously defined FinalTarget.
                continue
            yield i, Target(type=target_type, name=target_name)



def references_target(fsx_file, target):
    #again, this is also very approximate
    with open(fsx_file, 'r') as f:
        for line in f:
            if target.name in line: # we dont handle comments, abstraction, etc
                return True
    return False


def normalise_path(p, p_root, root):
    if not os.path.isabs(p):
        p = os.path.abspath(os.path.join(p_root, p))
    return os.path.normpath(os.path.join(root, os.path.relpath(p, root)))

def get_parent(p):
    return os.path.abspath(os.path.normpath(os.path.join(p, os.path.pardir)))


def main():
    parser = argparse.ArgumentParser(description='\n'.join([
        'a linter for build systems composed of many FAKE .fsx scripts that like to #load each other.',
        'any file matching "*.fsx" inside the project is assumed to be a build script.',
        'returns nonzero if your build scripts have errors.', ]))
    parser.add_argument('root', type=str, default='.', nargs='?', help='root path of your project. all *.fsx files inside your project are assumed to be build scripts')
    parser.add_argument('--log-level', type=str, default='INFO', help='log level. DEBUG, INFO (default), WARN, ERROR, CRITICAL')
    parser.add_argument('--pedantic', action='store_true', help='complain about more things')
    args = parser.parse_args()

    logger = make_logger()
    logger.setLevel(args.log_level)

    root = args.root
    logger.info('root path is %r', root)

    build_files = [os.path.normpath(x) for x in find(root, '*.fsx')]

    deps = []

    for x in build_files:
        for line_number, y_ in find_fsx_load_dependencies(x):
            # the desired result here is that both x and y are relative paths, relative to the root path.
            y = normalise_path(y_, get_parent(x), root)

            logger.debug("%r is #loaded by %r", y, x)
            deps.append(Dep(y, x, debug_file_name=x, debug_line_number=line_number))


    targets = defaultdict(set)

    for x in build_files:
        for line_number, target in find_build_target_defns(x):
            logger.debug("%r:%r declares %r", x, line_number, target)

            assert target not in targets[x]
            targets[x].add(target)

    errors = []

    def error(msg, *args):
        logger.error(msg, *args)
        errors.append((msg, args))

    # check to see if things are trying to #load other things that dont exist
    for dep in deps:
        if not os.path.exists(dep.src):
            error('%r:%r loads non-existent file %r', dep.debug_file_name, dep.debug_line_number, dep.src)

    if args.pedantic:
        # check to see if things are #load-ing other things without consuming their targets
        for dep in deps:
            # it should be the case that dep.dst references at least one target defined by dep.src. otherwise, why #load it?
            if not targets[dep.src]: # assume if we're loading things that contain no targets, we must want them for some other reason.
                continue
            if not any(references_target(dep.dst, t) for t in targets[dep.src]):
                error('%r loads %r without referencing any targets defined therein', dep.debug_file_name, dep.src)

    # check to see that target names are globally unique
    all_target_names = defaultdict(set)
    for x in targets:
        for t in targets[x]:
            if t.name in all_target_names:
                error('%r defines %r but a target of the same name, %r, is also defined in: %r', x, t, t.name, list(all_target_names[t.name]))
            else:
                all_target_names[t.name].add(x)

    if errors:
        logger.error('found %r error%s in build scripts' % (len(errors), '' if len(errors)==1 else 's'))
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()

