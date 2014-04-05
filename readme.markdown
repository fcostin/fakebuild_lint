fakebuild lint
==============


### usage

    $ ./fakebuild_lint.py --help

    usage: fakebuild_lint.py [-h] [--log-level LOG_LEVEL] [root]

    a linter for build systems composed of many FAKE .fsx scripts that like to
    #load each other. any file matching "*.fsx" inside the project is assumed to
    be a build script. returns nonzero if your build scripts have errors.

    positional arguments:
      root                  root path of your project. all *.fsx files inside your
                            project are assumed to be build scripts

    optional arguments:
      -h, --help            show this help message and exit
      --log-level LOG_LEVEL
                            log level. DEBUG, INFO (default), WARN, ERROR,
                            CRITICAL

### things that will be complained about

*   things that try to `#load` other things that dont exist
*   things that `#load` other things that contain `Target`s, without referencing any of those `Target`s
*   `Target` names that are not globally unique across the project

### disclaimer

*   no effort is made to parse / interpret f# code properly. results will be approximate.

### answers to questions that no-one has asked (cf. "faq")

*   isn't the target audience of this going to very small, and perhaps empty?
    +   yep.
*   why isn't this written in f#?
    +   i like writing things in python.
*   do you recommend constructing build systems out of many `.fsx` scripts that `#load` each other?
    +   no. the `#load` mechanism of f# scripts is lamentable, in that it does not like you `#load`-ing something twice, yet no mechanism like `#pragma once` or `#define` / `#ifndef` is provided.
*   couldn't you work around that problem by not making your "library" `.fsx` scripts `#load` anything, and write a top-level "main" `.fsx` script that `#load`s all transitive dependencies exactly once in the correct order?
    +   yes. yet that sounds strangely similar to what you might wish a build system to do for you.

### license

*   BSD 2-clause
