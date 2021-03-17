######################################################################
# Simple active-active example
# (C) 2006 Tail-f Systems
#
# See the README file for more information
######################################################################

usage:
	@echo "See README file for more instructions"
	@echo "make all      Build all example files"
	@echo "make clean    Remove all built and intermediary files"
	@echo "make start    Start ConfD daemons and active-active synchronizer agents"
	@echo "make stop     Stop any ConfD daemons and active-active synchronizer agents"


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

DO_DEBUG_LOG ?= #-DDO_DEBUG_LOG

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd --addloadpath .
START_FLAGS ?=

SRC	  = aasync.c
OBJS	  = $(SRC:.c=.o)

CFLAGS += $(DO_DEBUG_LOG)

ifeq ($(DO_DEBUG_LOG),-DDO_DEBUG_LOG)
  AASYNC_DEBUG = -t
  CCMD_DEBUG = -d -d
else
  AASYNC_DEBUG = -q
  CCMD_DEBUG =
endif

INIT_NODE        = 0
NODE 		 = 0
NNODES 		 = 3
NUMLE            = 1
NETCONF_SSH_BASE = 2022
NETCONF_BASE     = 2023
HTTP_BASE        = 8008
HTTPS_BASE       = 8888
IPC_BASE         = 4565

MAXNODE		= $(eval $NNODES - 1)

all:	routes.fxs routes.h aacluster.fxs aacluster.h node$MAXNODE/confd.conf aasync $(CDB_DIR) ssh-keydir
	@echo "Build complete"

aacluster.fxs: aacluster.yang
	$(CONFDC) -c --yangpath . -o $@ $<

aasync: $(OBJS)
	$(CC) -o $@ $(OBJS) $(LIBS)

routes.h:
	confdc --emit-h routes.h routes.fxs

######################################################################
clean:	iclean
	-rm -rf routes.h aacluster.h node* init.xml aasync confirm.xml del.xml 2> /dev/null || true

start:	stop
	@echo "### Start $(NNODES) confd aasync daemons with nodeid 0--$$(($(NNODES)-1))"
	@i=0; while [ $$i -lt $(NNODES) ]; do \
		echo "### Starting node$$i of $(NNODES) phase 0" ; \
		( cd node$$i ; $(CONFD) -c confd.conf --start-phase0 $(CONFD_FLAGS)) ; \
		i=$$(($$i + 1)) ; \
	      done
	@i=0; while [ $$i -lt $(NNODES) ]; do \
		echo "### Starting aasync$$i of $(NNODES)" ; \
		( cd node$$i ; ../aasync $(AASYNC_DEBUG) -n $$i &) ; \
		i=$$(($$i + 1)) ; \
	      done
	@echo "### Waiting for node0 to enter start-phase 2"
	@confd_cmd $(CCMD_DEBUG) -c "wait-start 2"

join:
	@echo "### Setting up node$(NODE)"
	rm -rf node$(NODE) ; \
	mkdir -p node$(NODE)/confd-cdb ;	\
	   ./cdbgen.py gen_join_cfg $(IPC_BASE) $(NODE) $(INIT_NODE) > node$(NODE)/confd-cdb/sync_init.xml ; \
	   sed -e "s|<!-- %NAME% -->|aasync$(NODE)|" \
			< sync_aaa_init.xml > node$(NODE)/confd-cdb/aaa_init.xml ; \
	   sed -e "s|<!-- %SSH-PORT% -->|$$(($(NETCONF_SSH_BASE)+10*$(NODE)))|" \
	       -e "s|<!-- %TCP-PORT% -->|$$(($(NETCONF_BASE)+10*$(NODE)))|" \
	       -e "s|<!-- %HTTP-PORT% -->|$$(($(HTTP_BASE)+10*$(NODE)))|" \
	       -e "s|<!-- %HTTPS-PORT% -->|$$(($(HTTPS_BASE)+10*$(NODE)))|" \
	       -e "s|<!-- %IPC% -->|$$(($(IPC_BASE)+10*$(NODE)))|" \
			< confd.conf > node$(NODE)/confd.conf
	@echo "### Start confd aasync daemon with nodeid $(NODE) and join cluster by connecting to nodeid 0"
	if [ 1 ]; then \
	  echo "### Starting node$(NODE)" ; \
	  cd node$(NODE) ; \
	  $(CONFD) -c confd.conf --start-phase0 $(CONFD_FLAGS) ; \
	  echo "### Starting aasync$(NODE)" ; \
	  (../aasync $(AASYNC_DEBUG) -n $(NODE) -j &) ; \
	fi

join3:
	@$(MAKE) NODE=3 NNODES=2 INIT_NODE=0 join
	@echo "### Waiting for node3 to enter start-phase 2"
	confd_cmd $(CCMD_DEBUG) -p $$(($(IPC_BASE)+10*3)) -c "wait-start 2"

leave:
	confd_cmd $(CCMD_DEBUG) -p $$(($(IPC_BASE)+10*$(NODE))) -c "mdel /r:active-cfg/a:aacluster/a:node{$(NODE)}"
	confd_cmd $(CCMD_DEBUG) -p $$(($(IPC_BASE)+10*$(NODE))) -c "stop"

leave3:
	@$(MAKE) NODE=3 leave

node%/confd.conf:
	@i=0; \
	while [ $$i -lt $(NNODES) ]; do \
	   echo "### Setting up node$$i" ; \
	   rm -rf node$$i ; \
	   mkdir -p node$$i/confd-cdb ;	\
	   ./cdbgen.py gen_data_seed $(NUMLE) $$i > node$$i/confd-cdb/init.xml ; \
	   ./cdbgen.py gen_sync_cfg $(IPC_BASE) $(NNODES) $(INIT_NODE) > node$$i/confd-cdb/sync_init.xml ; \
	   sed -e "s|<!-- %NAME% -->|aasync$$i|" \
			< sync_aaa_init.xml > node$$i/confd-cdb/aaa_init.xml ; \
	   sed -e "s|<!-- %SSH-PORT% -->|$$(($(NETCONF_SSH_BASE)+10*$$i))|" \
	       -e "s|<!-- %TCP-PORT% -->|$$(($(NETCONF_BASE)+10*$$i))|" \
	       -e "s|<!-- %HTTP-PORT% -->|$$(($(HTTP_BASE)+10*$$i))|" \
	       -e "s|<!-- %HTTPS-PORT% -->|$$(($(HTTPS_BASE)+10*$$i))|" \
	       -e "s|<!-- %IPC% -->|$$(($(IPC_BASE)+10*$$i))|" \
			< confd.conf > node$$i/confd.conf ; \
	   i=$$(($$i + 1)) ; \
	done

######################################################################
stop:
	@echo "###  Stop the confd daemons and active-active synchronizer agents"
	@i=0; while [ $$i -lt $(NNODES) ]; do \
		echo "### Stopping node$$i" ; \
		env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$$i)) $(CONFD) --stop ; \
		i=$$(($$i + 1)) ; \
	      done
	$(KILLALL) aasync || true

stop3:
	@$(MAKE) NNODES=4 stop
######################################################################
cli:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$(NODE))) \
		$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
			--interactive || echo Exit

cli1:
	@$(MAKE) NODE=1 cli

cli2:
	@$(MAKE) NODE=2 cli

cli3:
	@$(MAKE) NODE=3 cli

cli1-c:
	@$(MAKE) NODE=1 cli-c

cli2-c:
	@$(MAKE) NODE=2 cli-c

cli3-c:
	@$(MAKE) NODE=3 cli-c

cli-c:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$(NODE))) \
		$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
			--interactive || echo Exit

######################################################################
dxml:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$(NODE))) \
		$(CONFD_DIR)/bin/confd_load $(CCMD_DEBUG) -F p -p /active-cfg

dxml0:
	@$(MAKE) NODE=0 dxml

dxml1:
	@$(MAKE) NODE=1 dxml

dxml2:
	@$(MAKE) NODE=2 dxml

dxml3:
	@$(MAKE) NODE=3 dxml

######################################################################
dxmli:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$(NODE))) \
		$(CONFD_DIR)/bin/confd_load $(CCMD_DEBUG) -i -F p -p /active-cfg

dxml0i:
	@$(MAKE) NODE=0 dxmli

dxml1i:
	@$(MAKE) NODE=1 dxmli

dxml2i:
	@$(MAKE) NODE=2 dxmli

dxml3i:
	@$(MAKE) NODE=3 dxmli
