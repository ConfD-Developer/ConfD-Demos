######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''

######################################################################
# Example specific definitions and rules

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd --addloadpath . 
START_FLAGS ?=

CONFDC=$(CONFD_DIR)/bin/confdc

CLISPEC_SRCS        = $(wildcard *.cli)
CLISPECS            = $(patsubst %.cli, %.ccl, $(CLISPEC_SRCS))

YANG_SOURCES        = $(wildcard *.yang)
SUBMODULES          = $(shell grep -l belongs-to *.yang)
ANNOTATION_MODULES  = $(wildcard *-ann*.yang)
TAILF_MODULES       = $(wildcard tailf-*.yang)

BUILTIN_MODULES     += ietf-yang-types.yang
BUILTIN_MODULES     += ietf-inet-types.yang
BUILTIN_MODULES     += ietf-yang-library.yang

BUILTIN_MODULES     += ietf-netconf.yang
BUILTIN_MODULES     += ietf-netconf-acm.yang
BUILTIN_MODULES     += ietf-netconf-with-defaults.yang

BUILTIN_MODULES     += ietf-restconf.yang
BUILTIN_MODULES     += ietf-yang-patch.yang
BUILTIN_MODULES     += tailf-rest-error.yang
BUILTIN_MODULES     += tailf-rest-query.yang

YANG_MODULES = $(filter-out $(SUBMODULES) $(ANNOTATION_MODULES) \
		$(BUILTIN_MODULES) $(TAILF_MODULES) ,$(YANG_SOURCES))

ALL_FXS_FILES = $(YANG_MODULES:%.yang=%.fxs)

%.fxs: 	%.yang %-ann.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -a $*-ann.yang -- $<

%.fxs: 	%.yang
	$(CONFDC) -c --yangpath . --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -- $<

SRCS = $(wildcard *.c)
PROGS = $(patsubst %.c, %, $(SRCS))
HSS = $(ALL_FXS_FILES:.fxs=.h)

%: %.c
	$(CC) -o $@ -Wall -g $< $(CFLAGS) $(LIBS) $(EXTRA_LIBS)
######################################################################
all:	$(ALL_FXS_FILES) $(HSS) $(PROGS) $(CLISPECS) $(CDB_DIR) ssh-keydir
	@echo "Build complete"

######################################################################
clean:	iclean
	-rm -rf *.log *.trace cli-history *.fxs 2> /dev/null || true

######################################################################
start:  stop
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

######################################################################
stop:
	@ # Kill the confd daemon
	$(CONFD) --stop || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
	--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
	--interactive  || echo Exit

######################################################################
