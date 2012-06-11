#!/usr/bin/env python

from __future__ import print_function

import os.path as P
from optparse import OptionParser
from glob import glob
import shutil, sys, os
from datetime import datetime

def write_makefile_am_closing( directory, makefile, all_protoprefixes, CLEANFILES = [], BUILT_SOURCES = [] ):
    print('\nincludedir      = $(prefix)/include', file=makefile)
    print('\ninclude $(top_srcdir)/config/rules.mak\n', file=makefile)

    # Additional clean up for all of the auto generated files.
    if all_protoprefixes:
        directory_w_proto = \
            list(set([P.dirname(P.relpath(x,directory)) for x in all_protoprefixes]))
        print('AM_CXXFLAGS     += %s' % ' '.join(["-I$(srcdir)/%s" % x for x in directory_w_proto]), file=makefile)
        print('include_HEADERS = $(protocol_headers)', file=makefile)
        print('BUILT_SOURCES   = $(protocol_sources) %s' % ' '.join(BUILT_SOURCES), file=makefile)
        print('CLEANFILES      = $(protocol_headers) $(protocol_sources) %s' % ' '.join(CLEANFILES), file=makefile)
        print('EXTRA_DIST      = %s $(protocol_headers) $(protocol_sources)' % ' '.join([P.relpath(x + ".proto",directory) for x in all_protoprefixes]), file=makefile)
        print('include $(top_srcdir)/thirdparty/protobuf.mak', file=makefile)

def write_makefile_am_from_objs_dir_core( directory, moc_generated_files ):
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    all_protoprefixes = []
    sourcefiles = []
    for sdirectory in glob(P.join(directory,'*')):
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

        sourcefiles.extend( glob(P.join(sdirectory,'*.cpp')) )
        sourcefiles.extend( [x + ".pb.cc" for x in protoprefixes] )

    # Write out additional build sources from MOC
    additional_built_files = []
    for pair in moc_generated_files:
        moc_built = P.join( directory, P.basename(pair[1]),
                            pair[0].split('.')[0] + ".moc.cc" )
        additional_built_files.append( P.relpath(moc_built,directory) )
        sourcefiles.append( moc_built )

    # Write out the dependencies for libisis
    print('libisis3_la_SOURCES = ', file=makefile, end='')
    for source in sourcefiles:
        relative_source = P.relpath( source, directory )
        print(' \\\n  %s' % relative_source, file=makefile, end='')
    print('\n', file=makefile)
    print('lib_LTLIBRARIES = libisis3.la', file=makefile)
    write_makefile_am_closing( directory, makefile, all_protoprefixes,
                               additional_built_files, additional_built_files )

def write_makefile_am_from_objs_dir( directory ):
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    module_names = []
    all_protoprefixes = []
    for sdirectory in glob(P.join(directory,'*')):
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
    write_makefile_am_closing( directory, makefile, all_protoprefixes )

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--isisroot', dest='isisroot', default=None, help='Copy of ISIS to clone from')
    parser.add_option('--destination', dest='destination', default='isis_autotools', help='Directory to write reformatted ISIS release')
    parser.add_option('--basename', dest='basename', default='ISIS_AutoTools', help='Basename to use for output tarball')

    global opt
    (opt, args) = parser.parse_args()

    if opt.isisroot is None or not P.isdir(opt.isisroot):
        parser.print_help()
        print('\nIllegal argument to --isisroot: path does not exist')
        sys.exit(-1)

    # Copy in custom scripts and files that we use
    shutil.copytree( 'dist-add', P.join(opt.destination),
                     ignore=shutil.ignore_patterns('*~') )

    # Traverse the source tree an create a set of the plugins
    # files that exist. They'll determine where we'll put the object
    # folders.
    plugins = set()
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ):
        for plugin in [x for x in files if x.endswith('.plugin')]:
            plugins.add( plugin.split('.')[0] )

    print("Plugins available: [%s]" % ' '.join(plugins))
    os.mkdir( P.join( opt.destination, 'src' ) )
    for plugin in plugins:
        os.mkdir( P.join( opt.destination, 'src', plugin ) )
    os.mkdir( P.join( opt.destination, 'src', 'Core' ) )

    # Traverse and copy all files which are not make files or
    # headers. The destination is determined by the plugin file. If
    # there doesn't exist such a file ... then they get dumped into
    # the main core library.
    #
    # While we're here .. we'll copy the headers to include
    os.mkdir( P.join( opt.destination, 'include' ) )
    header_dir = P.join( opt.destination, 'include' )
    ignore_func = ignore=shutil.ignore_patterns('Makefile','apps','unitTest.cpp','tsts','*.h','*.truth','*.plugin','*.cub','*.xml')
    moc_generated_files = []
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ):
        root_split = root.split('/')
        if 'qisis' in root_split or 'docsys' in root_split:
            continue
        if root_split[-1] == "objs":
            for obj in dirs:
                # Look for a plugin file:
                plugin = [P.basename(x.split('.')[0]) for x in glob( P.join(root, obj, "*.plugin") )]
                if len(plugin) > 1:
                    print("ERROR: Found more than one plugin file!\n")
                    sys.exit()
                destination_sub_path = None
                if not plugin:
                    destination_sub_path = P.join( 'src', 'Core', obj )
                else:
                    destination_sub_path = P.join( 'src', plugin[0], obj )

                shutil.copytree( P.join( root, obj ),
                                 P.join( opt.destination, destination_sub_path),
                                 ignore=ignore_func )

                # Move headers to the include directory. If they need
                # to be MOC generated ... I'll do an ugly hack an just
                # make a softlink that points to the new header
                # location. This hack is required because ISIS expects
                # its headers all to be in one spot.
                headers = glob( P.join( root, obj, '*.h' ) )
                for header in headers:
                    shutil.copy( header, header_dir )
                    # See if this header needs an autogenerated MOC
                    # file.
                    for line in open( header ):
                        if "Q_OBJECT" in line:
                            moc_generated_files.append( [P.basename(header), destination_sub_path] )
                            symlink_output = P.join(opt.destination,destination_sub_path,
                                                    P.basename(header))
                            os.symlink( P.relpath(P.join(header_dir,P.basename(header)),
                                                  P.dirname(symlink_output) ),
                                        symlink_output )
                            break

    # Remove any directories which are empty (kaguya has no binaries)
    for root, dirs, files in os.walk( P.join(opt.destination, 'src'),
                                      topdown=False):
        dirs = [x for x in dirs if P.exists(P.join(root,x))]
        if not dirs and not files:
            os.rmdir( root )

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

    for plugin in plugins:
        write_makefile_am_from_objs_dir( P.join( opt.destination, 'src', plugin ) )
    write_makefile_am_from_objs_dir_core( P.join( opt.destination, 'src', 'Core' ),
                                          moc_generated_files )

    # Create extra directory which contains IsisPreferences and the
    # plugin files. The plugin files will need to be appended to each
    # other here. There is also a Makefile to tell autotools where to
    # install every thing.
    extra_dir = P.join( opt.destination, 'extra' )
    os.mkdir( extra_dir )
    shutil.copy( P.join( opt.isisroot, 'IsisPreferences' ),
                 extra_dir )
    shutil.copy( P.join( opt.isisroot, 'version' ),
                 extra_dir )
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ):
        for plugin in [x for x in files if x.endswith('.plugin')]:
            with open( P.join(extra_dir, plugin), 'ab' ) as dest_txt:
                shutil.copyfileobj(open( P.join( root, plugin ), 'rb' ),
                                   dest_txt )
    with open(P.join(opt.destination,'extra','Makefile.am'), 'w') as makefile:
        print('prefixdir = @prefix@', file=makefile)
        print('prefix_DATA = IsisPreferences version', file=makefile)
        print('mylibdir = $(libdir)', file=makefile)
        print('mylib_DATA = %s' % ' '.join( [x +".plugin" for x in plugins] ),
              file=makefile )
        print('EXTRA_DIST = IsisPreferences %s' % ' '.join( [x + ".plugin" for x in plugins] ),
              file=makefile )

    # Write a Makefile for all of the directories under 'src'
    plugins.add('Core')
    with open(P.join(opt.destination,'src','Makefile.am'), 'w') as makefile:
        print('SUBDIRS = ', file=makefile, end='')
        for dir in plugins:
            print(' \\\n  %s' % dir, file=makefile, end='')
        print('\n', file=makefile)

    # Write an incompassing makefile.am
    shutil.copy( 'config.options.example',
                 P.join( opt.destination ) )
    with open(P.join(opt.destination,'Makefile.am'), 'w') as makefile:
        print('ACLOCAL_AMFLAGS = -I m4', file=makefile)
        print('SUBDIRS = src include extra\n', file=makefile)
        # EXTRA_DIST are just objects that we want copied into the
        # distribution tarball for ISIS .. if we wish to do so.
        print('EXTRA_DIST = \\', file=makefile)
        print('  autogen config.options.example', file=makefile)

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

    # Create a tarball of everything and date it.
    version_number = ""
    with open(P.join(opt.isisroot,'version'), 'r') as f:
        version_number = f.readline()
        version_number = version_number[:version_number.find('#')].strip()
    tarball_name = "%s-%s-%s.tar.gz" % (opt.basename,version_number,str(datetime.now().date()))
    print("Creating tarball: %s" % tarball_name)
    os.system( "tar czf %s %s" % (tarball_name, opt.destination) )
