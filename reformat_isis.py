#!/usr/bin/env python

from __future__ import print_function

import os.path as P
from optparse import OptionParser
from glob import glob
import shutil, sys, os

def write_makefile_am_from_objs_dir( directory ):
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    module_names = []
    directories = glob(P.join(directory,'*'))
    all_protoprefixes = []
    for sdirectory in directories:
        if not P.isdir( sdirectory ):
            continue
        module_name = P.relpath( sdirectory, directory )

        # Check for protofiles which would need to be generated
        protoprefixes = [P.splitext(x)[0] for x in glob(P.join(sdirectory,'*.proto'))]
        if protoprefixes:
            operator_ = "="
            if all_protoprefixes:
                operator = "+="
            print('protocol_headers %s %s' %
                  (operator_,' '.join([P.relpath(x + ".pb.h",directory) for x in protoprefixes])), file=makefile)
            print('protocol_sources %s %s\n' %
                  (operator_,' '.join([P.relpath(x + ".pb.cc",directory) for x in protoprefixes])), file=makefile)
        all_protoprefixes.extend( protoprefixes )

        # Write instruction to create a shared library from the to be
        # compiled sources.
        sourcefiles = glob(P.join(sdirectory,'*.cpp'))
        sourcefiles.extend( [x + ".pb.cc" for x in protoprefixes] )
        if sourcefiles:
            module_names.append( module_name )
            print('lib%s_la_SOURCES = ' % module_name, file=makefile, end='')
            for source in sourcefiles:
                relative_source = P.relpath( source, directory )
                print(' \\\n  %s' % relative_source, file=makefile, end='')
            print('\n', file=makefile)

    print('lib_LTLIBRARIES   =', file=makefile, end='')
    for module in module_names:
        print(' lib%s.la' % module, file=makefile, end='')
    print('\nincludedir      = $(prefix)/include', file=makefile)
    print('\ninclude $(top_srcdir)/config/rules.mak\n', file=makefile)

    # Additional clean up for all of the auto generated files.
    if all_protoprefixes:
        print('include_HEADERS = $(protocol_headers)', file=makefile)
        print('BUILT_SOURCES   = $(protocol_sources)', file=makefile)
        print('CLEANFILES      = $(protocol_headers) $(protocol_sources)', file=makefile)
        print('EXTRA_DIST      = %s $(protocol_headers) $(protocol_sources)' % ' '.join([P.relpath(x + ".proto",directory) for x in all_protoprefixes]), file=makefile)
        print('include $(top_srcdir)/thirdparty/protobuf.mak', file=makefile)

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--isisroot', dest='isisroot', default=None, help='Copy of ISIS to clone from')
    parser.add_option('--destination', dest='destination', default='isis_autotools', help='Directory to write reformatted ISIS release')

    global opt
    (opt, args) = parser.parse_args()

    if opt.isisroot is None or not P.isdir(opt.isisroot):
        parser.print_help()
        print('\nIllegal argument to --isisroot: path does not exist')
        sys.exit(-1)

    # Copy in custom scripts and files that we use
    shutil.copytree( 'dist-add', P.join(opt.destination),
                     ignore=shutil.ignore_patterns('*~') )

    # Traverse and copy all files which are not make files or headers
    shutil.copytree( P.join(opt.isisroot,'src'),
                     P.join(opt.destination,'src'),
                     ignore=shutil.ignore_patterns('Makefile','apps','unitTest.cpp','tsts','*.h'))

    # Copy all headers into their own directory ... because ISIS
    # doesn't use paths in their '#includes'.
    os.mkdir( P.join( opt.destination, 'include' ) )
    header_dir = P.join( opt.destination, 'include' )
    for root, dirs, files in os.walk( P.join( opt.isisroot, 'src' ) ):
        headers = [h for h in files if h.endswith('.h')]
        for header in headers:
            shutil.copy( P.join(root, header ),
                         P.join(header_dir) )
    del header_dir

    # So Writing Makefile.am from directory contents
    # It should look something like the following.

    # include_HEADERS = Apollo/Apollo.h \
    #                   Metric/Metric.h

    # libApollo_la_SOURCES = Apollo/Apollo.cc
    # libApollo_la_LIBADD  = @MODULE_EVERYTHING@
    #
    # libMetric_la_SOURCES = Metric/Metric.cc
    # libMetric_la_LIBADD  = @MODULE_EVERYTHING@
    #
    # lib_LTLIBRARIES = libApollo.la libMetric.la
    #
    # includedir = $(prefix)/include
    for root, dirs, files in os.walk( opt.destination, topdown=False):
        if 'objs' in dirs:
            write_makefile_am_from_objs_dir( P.join( root, 'objs' ) )
        if not 'objs' in root.split('/') and \
                dirs and root != opt.destination:
            # Write a Makefile.am that tells only that there is a
            # subdirectory to traverse into.
            makefile = open(P.join(root,'Makefile.am'), 'w')
            print('SUBDIRS = ', file=makefile, end='')
            for dir in dirs:
                print(' \\\n  %s' % dir, file=makefile, end='')
            print('\n', file=makefile)

    # Write an incompassing makefile.am for each directory
    with open(P.join(opt.destination,'Makefile.am'), 'w') as makefile:
        print('ACLOCAL_AMFLAGS = -I m4', file=makefile)
        print('SUBDIRS = src include\n', file=makefile)
        # EXTRA_DIST are just objects that we want copied into the
        # distribution tarball for ISIS .. if we wish to do so.
        print('EXTRA_DIST = \\', file=makefile)
        print('  autogen', file=makefile)

    # Write a make file for the include/header directory
    with open(P.join(opt.destination,'include','Makefile.am'), 'w') as makefile:
        headers = glob(P.join(opt.destination,'include','*.h'))
        print('include_HEADERS = ', file=makefile, end='')
        for header in headers:
            relative_header = \
                P.relpath( header, P.join( opt.destination, 'include' ) )
            print(' \\\n  %s' % relative_header, file=makefile, end='')
        print('\n', file=makefile)
        print('\nincludedir = $(prefix)/include', file=makefile)

    # Generate configure.ac file that contains autogenerated information
    with open(P.join(opt.destination,'configure.ac'), 'w') as configure:
        configure_template = open(P.join(opt.destination,'configure.ac.in'), 'r')
        for line in configure_template:
            command = [x.strip() for x in line.split(' ')]
            if command[0] == 'PYTHON_INSERT_HERE':
                if command[1] == 'AC_CONFIG_FILES':
                    print('AC_CONFIG_FILES([ \\', file=configure)
                    # Do a search for all Makefile.am that are in the
                    # output directory.
                    for root, dirs, files in os.walk( opt.destination, topdown=False):
                        if 'Makefile.am' in files:
                            print('  %s/Makefile \\' % P.relpath( root, opt.destination ), file=configure)
                    print('])', file=configure)
            else:
                configure.write( line )
