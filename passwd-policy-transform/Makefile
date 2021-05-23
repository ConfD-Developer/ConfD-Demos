######################################################################
# AAA-Transform example
# (C) 2006 Tail-f Systems
#
# See the README file for more information
######################################################################

usage:
	@echo "See README file for more instructions"
	@echo "make all      Build all example files"
	@echo "make clean    Remove all built and intermediary files"
	@echo "make start    Start ConfD daemon and example agent"
	@echo "make stop     Stop any ConfD daemon and example agent"
	@echo "make query    Run NETCONF query against ConfD"
	@echo "make cli      Start the ConfD Command Line Interface"

######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''
	@exit 1

######################################################################
# Example specific definitions and rules

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd
START_FLAGS ?=

FXSS	= users.fxs
SRC	= users_aaa.c
OBJS	= $(SRC:.c=.o)

all:	$(FXSS) users.h users_aaa ssh-keydir \
		$(CDB_DIR)/aaa_init.xml
	@echo "Build complete"

users_aaa: $(OBJS)
	$(CC) -o $@ $(OBJS) $(LIBS)

$(OBJS): $(FXSS:.fxs=.h)


## need this particular vsn of aaa_init.xml for this example
$(CDB_DIR)/aaa_init.xml: aaa_init.xml
	-mkdir -p $(CDB_DIR)
	cp $< $@

######################################################################
clean:	iclean
	-rm -rf users_aaa users.h aaa.h \
		2> /dev/null || true

start:  stop 
	$(CONFD) -c confd.conf $(CONFD_FLAGS) 
	./users_aaa $(START_FLAGS) &

######################################################################
stop:
	$(CONFD) --stop    || true
	$(KILLALL) users_aaa || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

######################################################################
cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive || echo Exit

######################################################################
query:
	$(CONFD_DIR)/bin/netconf-console-tcp -u admin --get-config

######################################################################
