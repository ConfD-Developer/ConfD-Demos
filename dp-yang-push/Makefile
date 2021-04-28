######################################################################
# See the README file for more information
######################################################################

usage:
	@echo "See README file for more instructions"
	@echo "make all     Build all example files"
	@echo "make clean   Remove all built and intermediary files"
	@echo "make start   Start CONFD daemon and example agent"
	@echo "make stop    Stop any CONFD daemon and example agent"
	@echo "make query   Run query against CONFD"
	@echo "make cli     Start the CONFD Command Line Interface, J-style"
	@echo "make cli-c   Start the CONFD Command Line Interface, C-style"


######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''

######################################################################
# Example specific definitions and rules
CONFD_FXS_DIR = $(CONFD_DIR)/etc/confd
CONFD = $(CONFD_DIR)/bin/confd
CONFD_FLAGS = --addloadpath $(CONFD_FXS_DIR)
START_FLAGS ?= 10
LIBS += -lstdc++ -pthread
SRC  = route-status.cpp

YANG = route-status.yang
BIN = route-status

CFLAGS +=  -I$(CONFD_DIR)/examples.confd/include -DT_LOG_WARN
CPPFLAGS=$(CFLAGS) -std=c++0x

OBJS = $(SRC:.cpp=.o)
FXS = $(YANG:.yang=.fxs)
YANG_H = $(YANG:.yang=.h)


$(BIN): $(OBJS)
	g++ -o $@ $(OBJS) $(LIBS)

all: $(FXS) route-status_ns.py $(YANG_H) $(BIN) $(CDB_DIR) ssh-keydir
	@echo "Build complete"

######################################################################
clean:	iclean clean_perf_data
	rm -rf *.trace 2> /dev/null || true
	rm -rf cli-history 2> /dev/null || true
	rm -rf $(YANG_H) $(BIN) route_status_ns.py __init__.py

clean_perf_data:
	rm -rf dp-route*.xml

start_confd:  stop_confd
	### Start the confd daemon with our example specific confd-config
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

start_app:
	./$(BIN) $(START_FLAGS) &
	@echo 'Application started'

start: stop start_confd start_app

######################################################################
stop_confd:
	### Killing any confd daemon
	$(CONFD) --stop    || true

stop_app:
	$(KILLALL) $(BIN) || true
	@echo 'Application stopped'

stop: stop_confd stop_app


periodic-subscription: periodic-subscription.xml
	(cat $<; echo) | netconf-console -i -v 1.1

on-change-subscription: on-change-subscription.xml
	(cat $<; echo) | netconf-console -i -v 1.1
######################################################################
cli: cli-j

cli-j:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive || echo Exit
