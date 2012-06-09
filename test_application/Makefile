LIBTOOL = glibtool

QT_DIR = $(HOME)/packages/base_system/extra_install

# Protobuf, Xercesc, Geos, GSL
EXTRA_DIR = $(HOME)/packages/base_system/extra_install

# ISIS has a lot of dependencies ... so unfortunately what is below is written for my test system.
CXXFLAGS := -I../isis_autotools/build/include -I$(HOME)/packages/base_system/include -I$(HOME)/packages/base_system/extra_install/include
LDFLAGS  := -L../isis_autotools/build/lib -lisis3

CXXFLAGS += -I$(QT_DIR)/include/QtCore
LDFLAGS  += -L$(QT_DIR)/lib -lQtCore -lQtGui
LDFLAGS  += -L$(EXTRA_DIR)/lib -lxerces-c -lprotobuf -lgeos -lgsl -lcspice

%.o : %.cc
	$(LIBTOOL) --mode=compile $(CXX) -c -o $@ $(CXXFLAGS) $^

test: test.o
	$(LIBTOOL) --mode=link $(CXX) -o $@ $(CXXFLAGS) $(LDFLAGS) $^

clean:
	rm test test.o test.lo