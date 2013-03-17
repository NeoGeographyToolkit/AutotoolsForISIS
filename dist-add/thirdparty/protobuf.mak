########################################################################
# rules for compiling Google Protocol Buffers (using protoc)
########################################################################

SUFFIXES += .proto .pb.cc

PROTOC_ARGS =

# This bit of pwd uglyness is because autoconf 2.59 & automake 1.9.6 don't
# canonicalize abs_top_srcdir... instead it ends up being relative to
# $abs_srcdir (e.g. $abs_srcdir/../../). Protobuf can't handle relative paths.

.proto.pb.cc :
	$(AM_V_GEN)( \
		FILEDIR=`cd $$(dirname $<) && pwd` ;\
		SRC=`cd $(abs_srcdir)/$$(dirname $<) && pwd` ;\
		OBJ=`cd $(abs_builddir)/$$(dirname $<) && pwd` ;\
		FILENAME="$$FILEDIR/$$(basename $<)" ;\
                PREFIX="$$(basename $< | sed 's|\(.*\)\..*|\1|g')" ;\
		cd "$$SRC" && \
		$(PROTOC) -I"$$SRC" -I"$$OBJ" --cpp_out="$$OBJ" $(PROTOC_ARGS) "$$FILENAME" ;\
                mv "$$OBJ"/"$$PREFIX".pb.h $(abs_top_builddir)/include/ \
	)
