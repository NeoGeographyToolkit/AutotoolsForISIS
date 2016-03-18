#!/usr/bin/env python

# __BEGIN_LICENSE__
#  Copyright (c) 2009-2012, United States Government as represented by the
#  Administrator of the National Aeronautics and Space Administration. All
#  rights reserved.
#
#  The NGT platform is licensed under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance with the
#  License. You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# __END_LICENSE__

from __future__ import print_function

import os.path as P
from optparse import OptionParser
from glob import glob
import shutil, sys, os, subprocess
from datetime import datetime

def write_makefile_am_closing( directory, makefile, all_protoprefixes=[], CLEANFILES = [], BUILT_SOURCES = [], EXTRA_DIST = [] ):
    '''Close off a makefile written by one of the other functions.'''
    print('\nincludedir      = $(prefix)/include', file=makefile)
    print('\ninclude $(top_srcdir)/config/rules.mak\n', file=makefile)

    # Additional clean up for all of the auto generated files.
    if all_protoprefixes:
        directory_w_proto = \
            list(set([P.dirname(P.relpath(x,directory)) for x in all_protoprefixes]))
        print('AM_CXXFLAGS     += %s' % ' '.join(["-I$(srcdir)/%s" % x for x in directory_w_proto]), file=makefile)
        print('include_HEADERS = $(protocol_headers)', file=makefile)
        print('EXTRA_DIST      = %s $(protocol_headers) $(protocol_sources) %s' % (' '.join([P.relpath(x + ".proto",directory) for x in all_protoprefixes]),' '.join(EXTRA_DIST)), file=makefile)
        print('include $(top_srcdir)/thirdparty/protobuf.mak', file=makefile)
    if BUILT_SOURCES:
        print('BUILT_SOURCES   = $(protocol_sources) %s' % ' '.join(BUILT_SOURCES), file=makefile)
    if CLEANFILES:
        print('CLEANFILES      = $(protocol_headers) $(protocol_sources) %s' % ' '.join(CLEANFILES), file=makefile)



def write_makefile_am_from_objs_dir_core( directory,
                                          header_directory,
                                          moc_generated_files ):
    '''Makefile writer for an /objs directory in the /core folder'''
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    all_protoprefixes = []
    sourcefiles = []
    for sdirectory in glob(P.join(directory,'*')): # Loop through all folders in this directory
        if not P.isdir( sdirectory ):
            continue
        module_name = P.relpath( sdirectory, directory ) # Each folder corresponds to a module

        # Check for protofiles which would need to be generated
        protoprefixes = [P.splitext(x)[0] for x in glob(P.join(sdirectory,'*.proto'))]
        if protoprefixes:
            operator_ = "="
            if all_protoprefixes:
                operator = "+=" # Is this a bug?
            print('protocol_headers %s %s' %
                  (operator_,' '.join([P.relpath(P.join(header_directory,P.basename(x)+".pb.h"),directory) for x in protoprefixes])), file=makefile)
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
    print('libisis3_la_LIBADD = @PKG_ISISALLDEPS_LIBS@', file=makefile)
    print('lib_LTLIBRARIES = libisis3.la', file=makefile)
    write_makefile_am_closing( directory, makefile, all_protoprefixes,
                               additional_built_files, additional_built_files )

def write_makefile_am_from_apps_dir( directory, moc_generated_files ):
    '''Makefile writer for an /apps directory'''
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    # For some reason ISIS repeats a lot of headers and source
    # files. I think they actually compile some of their sources
    # multiple times.
    #
    # To save on errors from autogen, we must keep a dictionary of files
    sources_thus_far = []

    app_names = []
    moc_sources = []
    xml_files = []
    for sdirectory in glob(P.join(directory,'*')): # Loop through all folders in the directory
        if not P.isdir( sdirectory ):
            continue
        app_name = P.relpath( sdirectory, directory ).split(".")[0] # Each folder is an app

        # Identify XML files
        xml_files.extend( P.relpath(x, directory) for x in glob(P.join(sdirectory,'*.xml')) )

        # Write instructions to create an executable from the sources
        sourcefiles = glob(P.join(sdirectory,'*.cpp'))
        if sourcefiles:
            app_names.append( app_name )
            print('%s_SOURCES = ' % app_name, file=makefile, end='')
            ld_add = []
            for source in sourcefiles:
                relative_source = P.relpath( source, directory )
                filename = P.relpath( source, sdirectory )
                if filename in sources_thus_far:
                    ld_add.append("%s.$(OBJEXT)" % filename.split('.')[0])
                else:
                    sources_thus_far.append(filename)
                    print(' \\\n  %s' % relative_source, file=makefile, end='')
            # Identify headers that need to be moc generated
            for header in glob(P.join(sdirectory,'*.h')):
                for line in open( header ):
                    if "Q_OBJECT" in line:
                        moc_sources.append( "%s.dir/%s.moc.cc" % (app_name,P.basename(header).split('.')[0]) )
                        print(' \\\n  %s' % moc_sources[-1], file=makefile, end='')
                        break
            print('\n', file=makefile, end='')
            ld_add.append("../src/Core/libisis3.la") # They're referenced by directory path
            # Mission specific stuff is DLopened I believe.
            print('%s_LDADD = %s' % (app_name, " ".join(ld_add)), file=makefile)
            print('%s_CFLAGS = $(AM_CFLAGS)' % app_name, file=makefile)
            print('\n', file=makefile, end='')

    print('bin_PROGRAMS =', file=makefile, end='')
    for app in app_names:
        print(' %s' % app, file=makefile, end='')
    print('', file=makefile)

    # Write out where the XML files should be installed
    print('xmlhelpdir = $(bindir)/xml', file=makefile)
    print('xmlhelp_DATA = %s' % ' '.join(xml_files), file=makefile)

    write_makefile_am_closing( directory, makefile, [], moc_sources, moc_sources, xml_files )

def write_makefile_am_from_objs_dir( directory ):
    '''Makefile writer for an /objs directory OUTSIDE the /core folder, ie a plugin folder.'''
    makefile = open(P.join(directory,'Makefile.am'), 'w')

    module_names = []
    all_protoprefixes = []
    for sdirectory in glob(P.join(directory,'*')): # Loop through all folders in this directory
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
            print('lib%s_la_LIBADD = @PKG_ISISALLDEPS_LIBS@' % module_name, file=makefile)

    print('lib_LTLIBRARIES   =', file=makefile, end='')
    for module in module_names:
        print(' lib%s.la' % module, file=makefile, end='')
    write_makefile_am_closing( directory, makefile, all_protoprefixes )

#--------------------------------------------------------------------------------------------
# The main function!
if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--isisroot',        dest='isisroot',      default=None, help='Copy of ISIS to clone from')
    parser.add_option('--destination',     dest='destination',   default='isis_autotools', help='Directory to write reformatted ISIS release')
    parser.add_option('--basename',        dest='basename',      default='ISIS_AutoTools', help='Basename to use for output tarball')
    parser.add_option('--dont-build-apps', dest='dontBuildApps', default=False, action='store_true', help="Don't build any applications")

    global opt
    (opt, args) = parser.parse_args()

    if opt.isisroot is None or not P.isdir(opt.isisroot):
        parser.print_help()
        print('\nIllegal argument to --isisroot: path does not exist')
        sys.exit(-1)

    reformater_dir = P.dirname(P.realpath(__file__))

    # Copy all of the custom scripts and files that we use to the output directory
    shutil.copytree( P.join( reformater_dir, 'dist-add'),
                     P.join(opt.destination),
                     ignore=shutil.ignore_patterns('*~') )

    # Traverse the source tree and create a set of the plugins
    # files that exist. They will determine where we'll put the object folders.
    # - The plugin files themselves are actually tiny little config files.
    # - There are only a handful of plugin file names, but the same name appears in 
    #   multiple locations and the contents differ.
    plugins = set()
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ):
        for plugin in [x for x in files if x.endswith('.plugin')]:
            plugins.add( plugin.split('.')[0] )

    print("Plugins available: [%s]" % ' '.join(plugins))
    os.mkdir( P.join( opt.destination, 'src' ) )
    for plugin in plugins:
        os.mkdir( P.join( opt.destination, 'src', plugin ) )
    os.mkdir( P.join( opt.destination, 'src', 'Core' ) )
    os.mkdir( P.join( opt.destination, 'apps' ) )

    # Traverse and copy all files which are not make files or
    # headers. The destination is determined by the plugin file. If
    # there doesn't exist such a file ... then they get dumped into
    # the main core library.
    # - The organization here is that all of the folders with a .plugin file
    #   define specialized implementations of a generic class.  In our build
    #   we dump all plugins of the same type into a folder at the same level as core.
    # - Some files that were in /isis/name/sub before are now in /isis/core/name now.
    # - Why do we do this?

    # While we're here .. we'll copy the headers to include
    # - ISIS has duplicates of the include files in /inc and /src, but we only have
    #   them once in /include.
    os.mkdir( P.join( opt.destination, 'include' ) )
    header_dir = P.join( opt.destination, 'include' )
    
    # Ignore functions for /obj folders and /app folders
    ignore_func_obj = ignore=shutil.ignore_patterns('Makefile','apps','unitTest.cpp','tsts','*.h','*.truth','*.plugin','*.cub','*.xml')
    ignore_func_app = ignore=shutil.ignore_patterns('Makefile','apps','unitTest.cpp','tsts','*.truth','*.plugin','*.cub')
    
    # Blacklisted applications are apps we don't build because we
    # chose not to build the qisis module. This is the gui heavy
    # applications.
    #
    # Dropped Phohillier & spkwriter because I couldn't figure out the
    # linking bug. Probaby a link order thing?
    # Dropped cam2map since our built version does not work.
    app_blacklist = ["cnethist","hist","phohillier","spkwriter","cam2map"]
    moc_generated_obj = []
    moc_generated_app = []
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ):
        root_split = root.split('/')
        if 'qisis' in root_split or 'docsys' in root_split: # We also don't build their documentation
            continue
            
        # Handle stuff in the apps folders
        if (root_split[-1] == "apps") and (not opt.dontBuildApps):
            for app in dirs:
                if app in app_blacklist:
                    continue
                # In ISIS, the apps are in as /apps folder alongside an associated /objs folder.
                # We move everything from the various /apps folders into a single top level /apps folder.
                shutil.copytree( P.join( root, app ),
                                 P.join( opt.destination, 'apps', app+".dir" ),
                                 ignore=ignore_func_app ) # This call will copy the headers to

                # Identify headers that need to be processed through MOC (QT's Meta-Object Compiler)
                headers = glob( P.join( root, app, '*.h') )
                for header in headers:
                    for line in open( header ):
                        if "Q_OBJECT" in line:
                            moc_generated_app.append( [P.basename(header), P.join( 'apps', app+".dir" )] )
                            break
                            
        # Handle stuff in the objs folders
        if root_split[-1] == "objs":
            for obj in dirs:
                # Look for a plugin file:
                plugin = [P.basename(x.split('.')[0]) for x in glob( P.join(root, obj, "*.plugin") )]
                if len(plugin) > 1:
                    print("ERROR: Found more than one plugin file!\n")
                    sys.exit()
                destination_sub_path = None
                if not plugin: # Goes in Core
                    destination_sub_path = P.join( 'src', 'Core', obj )
                else: # Goes in the plugin folder we created earlier
                    destination_sub_path = P.join( 'src', plugin[0], obj )

                shutil.copytree( P.join( root, obj ),
                                 P.join( opt.destination, destination_sub_path),
                                 ignore=ignore_func_obj ) # This call does not copy headers

                # Move headers to the include directory. If they need
                # to be MOC generated ... I'll do an ugly hack and just
                # make a softlink that points to the new header
                # location. This hack is required because ISIS expects
                # its headers all to be in one spot.
                headers = glob( P.join( root, obj, '*.h' ) )
                for header in headers:
                    shutil.copy( header, header_dir )
                    # See if this header needs an autogenerated MOC file.
                    for line in open( header ):
                        if "Q_OBJECT" in line:
                            moc_generated_obj.append( [P.basename(header), destination_sub_path] )
                            symlink_output = P.join(opt.destination,destination_sub_path,
                                                    P.basename(header))
                            os.symlink( P.relpath(P.join(header_dir,P.basename(header)),
                                                  P.dirname(symlink_output) ),
                                        symlink_output )
                            break

    # Remove any destination directories which are empty (kaguya has no binaries)
    for root, dirs, files in os.walk( P.join(opt.destination, 'src'),
                                      topdown=False):
        dirs = [x for x in dirs if P.exists(P.join(root,x))]
        if not dirs and not files:
            os.rmdir( root )


    # Need to copy some more files from the inc dir that were not copied so far
    inc_dir=P.join(opt.isisroot, 'inc')
    headers = glob( P.join( inc_dir, '*.h') )
    for src in headers:
        dst = P.join(header_dir, os.path.basename(src))
        if not os.path.exists(dst):
            print("copy ", dst)
            shutil.copyfile(src, dst)
            

    #del header_dir

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

    # Generate plugin and core makefiles
    for plugin in plugins:
        write_makefile_am_from_objs_dir( P.join( opt.destination, 'src', plugin ) )
    write_makefile_am_from_objs_dir_core( P.join( opt.destination, 'src', 'Core' ),
                                          P.join( opt.destination, 'include' ),
                                          moc_generated_obj )

    # Write a makefile for all the apps
    write_makefile_am_from_apps_dir( P.join( opt.destination, 'apps' ),
                                     moc_generated_app )

    # Create extra directory which contains IsisPreferences and the
    # plugin files. The plugin files will need to be appended to each
    # other here in a single file. There is also a Makefile to tell 
    # autotools where to install everything.
    extra_dir = P.join( opt.destination, 'extra' )
    os.mkdir( extra_dir )
    shutil.copy( P.join( opt.isisroot, 'IsisPreferences' ), extra_dir )
    shutil.copy( P.join( opt.isisroot, 'version' ),         extra_dir )
    
    for root, dirs, files in os.walk( P.join(opt.isisroot, 'src') ): # Loops to append the plugin files
        for plugin in [x for x in files if x.endswith('.plugin')]:
            with open( P.join(extra_dir, plugin), 'ab' ) as dest_txt:
                shutil.copyfileobj(open( P.join( root, plugin ), 'rb' ), dest_txt )
                
    with open(P.join(opt.destination,'extra','Makefile.am'), 'w') as makefile: # The install makefile?
        print('prefixdir = @prefix@', file=makefile)
        print('prefix_DATA = IsisPreferences version', file=makefile)
        print('mylibdir = $(libdir)', file=makefile)
        print('mylib_DATA = %s' % ' '.join( [x +".plugin" for x in plugins] ),
              file=makefile )
        print('EXTRA_DIST = IsisPreferences %s' % ' '.join( [x + ".plugin" for x in plugins] ),
              file=makefile )

    # Write a Makefile for all of the directories under 'src'
    # - Just a simple listing of the subdirectories
    plugins.add('Core')
    with open(P.join(opt.destination,'src','Makefile.am'), 'w') as makefile:
        print('SUBDIRS = ', file=makefile, end='')
        for dir in plugins:
            print(' \\\n  %s' % dir, file=makefile, end='')
        print('\n', file=makefile)

    # Write an incompassing makefile.am
    # - Very little in this file.
    shutil.copy( P.join( reformater_dir, 'config.options.example' ),
                 P.join( opt.destination ) )
    with open(P.join(opt.destination,'Makefile.am'), 'w') as makefile:
        print('ACLOCAL_AMFLAGS = -I m4', file=makefile)
        print('SUBDIRS = src include extra apps\n', file=makefile)
        # EXTRA_DIST are just objects that we want copied into the
        # distribution tarball for ISIS .. if we wish to do so.
        print('EXTRA_DIST = \\', file=makefile)
        print('  autogen config.options.example', file=makefile)

    # Write a make file for the include/header directory
    # - Just one big include list and the include directory
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
    # - The real work has already been done in the /dist-add/configure.ac.in file
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

    # Apply Patches
    for patch in glob( P.join( reformater_dir, 'patches','*') ):
        cmd = ['patch','-p0','-i',patch]
        subprocess.check_call(cmd,cwd=opt.destination)

    # Remove requirement on CHOLMOD directory and remove UFConfig.h
    # - Why?
    print(opt.destination)
    subprocess.check_call(['pwd'],cwd=opt.destination)
    cmd = ['sed','-i','-e','s#CHOLMOD/##g','include/BundleAdjust.h']
    subprocess.check_call(cmd,cwd=opt.destination)
    cmd = ['sed','-i','-e','s#UFconfig#SuiteSparse_config#g','include/BundleAdjust.h']
    subprocess.check_call(cmd,cwd=opt.destination)

    # Create a tarball of everything and date it.
    version_number = ""
    with open(P.join(opt.isisroot,'version'), 'r') as f:
        version_number = f.readline()
        version_number = version_number[:version_number.find('#')].strip()
    tarball_name = "%s-%s-%s.tar.gz" % (opt.basename,version_number,str(datetime.now().date()))
    print("Creating tarball: %s" % tarball_name)
    os.system( "tar czf %s %s" % (tarball_name, opt.destination) )
