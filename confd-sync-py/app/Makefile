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

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd --addloadpath ../fxs --ignore-initial-validation
START_FLAGS ?=

NODE 		 = 0
NNODES 		 ?= 2
NETCONF_SSH_BASE ?= 12022
NETCONF_BASE     ?= 12023
HTTP_BASE        ?= 8008
HTTPS_BASE       ?= 8888
IPC_BASE         ?= 4565

CONFDC=$(CONFD_DIR)/bin/confdc

YANG_SOURCES        = $(wildcard yang/*.yang)
SUBMODULES          = $(shell grep -l belongs-to yang/*.yang)
ANNOTATION_MODULES  = $(wildcard yang/*-ann*.yang)
TAILF_MODULES       = $(wildcard yang/tailf-*.yang)

BUILTIN_MODULES     += yang/ietf-yang-types.yang
BUILTIN_MODULES     += yang/ietf-inet-types.yang
BUILTIN_MODULES     += yang/ietf-yang-library.yang

BUILTIN_MODULES     += yang/ietf-netconf.yang
BUILTIN_MODULES     += yang/ietf-netconf-acm.yang
BUILTIN_MODULES     += yang/ietf-netconf-with-defaults.yang

BUILTIN_MODULES     += yang/ietf-restconf.yang
BUILTIN_MODULES     += yang/ietf-yang-patch.yang
BUILTIN_MODULES     += yang/tailf-rest-error.yang
BUILTIN_MODULES     += yang/tailf-rest-query.yang

YANG_MODULES = $(filter-out $(SUBMODULES) $(ANNOTATION_MODULES) \
		$(BUILTIN_MODULES) $(TAILF_MODULES) ,$(YANG_SOURCES))

ALL_FXS_FILES = $(YANG_MODULES:yang/%.yang=fxs/%.fxs)
FXS_DIR = ./fxs

fxs/%.fxs: 	yang/%.yang yang/%-ann.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -a yang/$*-ann.yang -- $<

fxs/%.fxs: 	yang/%.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -- $<

$(FXS_DIR):
	-mkdir -p $(FXS_DIR)

######################################################################
all:	$(FXS_DIR) $(ALL_FXS_FILES) node$MAXNODE/confd.conf ssh-keydir
	@echo "Build complete"

######################################################################
clean:	iclean
	-rm -rf node* fxs subnodes.xml 2> /dev/null || true

######################################################################
start:  stop
	@echo "### Start $(NNODES) confd daemons with our example specific confd-conf"
	@i=0; while [ $$i -lt $(NNODES) ]; do \
		echo "Starting node$$i" ; \
		( cd node$$i ; env sname=node$$i \
			 $(CONFD) -c confd.conf $(CONFD_FLAGS) ) ; \
		i=$$(($$i + 1)) ; \
	      done

start%:
	@echo "###  Start confd daemon $*"
	( cd node$* ; env sname=node$* $(CONFD) -c confd.conf $(CONFD_FLAGS));

node%/confd.conf:
	@i=0; \
	while [ $$i -lt $(NNODES) ]; do \
	   echo "Setting up node$$i" ; \
	   rm -rf node$$i ; \
	   mkdir -p node$$i/confd-cdb ;	\
	   cp $(CONFD_DIR)/var/confd/cdb/aaa_init.xml node$$i/confd-cdb ; \
	   sed -e "s|<!-- %SSH-PORT% -->|$$(($(NETCONF_SSH_BASE)+10*$$i))|" \
	       -e "s|<!-- %TCP-PORT% -->|$$(($(NETCONF_BASE)+10*$$i))|" \
	       -e "s|<!-- %HTTP-PORT% -->|$$(($(HTTP_BASE)+10*$$i))|" \
	       -e "s|<!-- %HTTPS-PORT% -->|$$(($(HTTPS_BASE)+10*$$i))|" \
	       -e "s|<!-- %IPC% -->|$$(($(IPC_BASE)+10*$$i))|" \
			< confd.conf.in > node$$i/confd.conf ; \
	   i=$$(($$i + 1)) ; \
	done

######################################################################
stop:
	@echo "###  Stop the confd daemons"
	@i=0; while [ $$i -lt $(NNODES) ]; do \
		echo "Stopping node$$i" ; \
		env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$$i)) $(CONFD) --stop ; \
		i=$$(($$i + 1)) ; \
	      done

stop%:
	@echo "###  Stop confd daemon $*"
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$*)) $(CONFD) --stop

######################################################################
cli%:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$*)) \
		$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
			--interactive || echo Exit

cli-c%:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$*) \
		$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
			--interactive || echo Exit

######################################################################
query%:
	$(CONFD_DIR)/bin/netconf-console -snoaaa --get-config --port=$$(($(NETCONF_SSH_BASE)+10*$*))

######################################################################
status%:
	env CONFD_IPC_PORT=$$(($(IPC_BASE)+10*$*)) $(CONFD) --status

######################################################################
