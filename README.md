# Autotools applier for USGS ISIS 3.+

This provides a build system that is more compatible with the open
source community. Autotools is a long standing build system that has
been popularized by the GNU movement. To learn more about Autotools,
please read the following:

http://en.wikipedia.org/wiki/GNU_build_system

## How to use this project

This is still a work in progress. At the time of this writing, this
build system doesn't work well enough to actually compile anything. It
just applies the build system.

```bash
> Download ISIS
> ./reformat_isis.py --isisroot=$YOUR_ISIS_ROOT_THAT_YOU_JUST_DOWNLOADED
> cd isis_autotools
> ./autogen
> ./configure <use some settings here>
> make -j N
> make install
```

Then you party. You are the one and only master of build
systems. (Besides the other people who checked out this project.)