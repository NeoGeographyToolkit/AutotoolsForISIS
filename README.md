# Autotools applier for USGS ISIS 3.+

This provides a build system that is more compatible with the open
source community. Autotools is a long standing build system that has
been popularized by the GNU movement. To learn more about Autotools,
please read the following:

http://en.wikipedia.org/wiki/GNU_build_system

## How to use this project

This project is by its very nature is fragile. Use it as an example
for how to build ISIS with autotools. Our purpose for this project is
to build a copy of ISIS for our distributions of Ames Stereo
Pipeline. If you'd like to see those build scripts, take a look at our
BinaryBuilder project. It is essentially a package manager.

https://github.com/NeoGeographyToolkit/BinaryBuilder

```bash
> Download the Mac OSX version ISIS. We don't care if doesn't run on your system. We're pillaging it for its source code.
> ./reformat_isis.py --isisroot=$YOUR_ISIS_ROOT_THAT_YOU_JUST_DOWNLOADED
> cd isis_autotools
> ./autogen
> ./configure <use some settings here>
> make -j N
> make install
```

Then you party. You are the one and only master of build
systems. (Besides the other people who checked out this project.)