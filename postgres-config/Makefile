######################################################################
# Simple example
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

CONFD_CONF  = confd.conf
CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd
START_FLAGS ?=

OSTYPE	= $(shell uname -s)
CFLAGS	+= -D$(OSTYPE)
SRC	  = servers.c
OBJS	  = $(SRC:.c=.o)

ifeq ($(EXTRA_GDB),yes)
CFLAGS += -O0 -g3
endif

ifeq ($(EXTRA_WARNING),yes)
CFLAGS += -Wextra -Wformat-nonliteral -Wformat-security
endif

GCCVER  = $(shell gcc --version | head -n 1 | awk '{print $$4}')

ifeq ($(OSTYPE),Linux)
#ifneq ($(word 1,$(sort $(GCCVER) 5.2.1)),5.2.1)
CFLAGS  += -std=gnu99
#endif
endif

######################################################################
all:	servers.fxs servers.h servers createdb $(CDB_DIR) ssh-keydir
	@echo "Build complete"

servers: servers.o
	$(CC) -o $@ $? $(LIBS) -lpq

createdb: createdb.o
	$(CC) -o $@ $? -lpq

######################################################################
clean:	iclean
	-rm -rf servers.h servers createdb *.trace 2> /dev/null || true

clean-history:
	-rm -rf cli-history

start:  stop
	$(CONFD) -c ./confd.conf $(CONFD_FLAGS)
	### * In one terminal window, run: tail -f ./confd.log
	### * In another terminal window, run queries
	###   (try 'make query' for an example)
	### * In this window, the HOSTS confd daemon now starts:
	./servers $(START_FLAGS)

######################################################################
stop:
	### Killing any confd daemon and simple_withtrans confd agents
	$(CONFD) --stop || true
	$(KILLALL) servers || true

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
	$(CONFD_DIR)/bin/netconf-console-tcp cmd-get-servers.xml

######################################################################
create-db:
	dropdb servers --if-exists
	sleep 1
	sudo -u postgres createdb  -e servers --owner <jojohans>
	sleep 1
	./createdb
