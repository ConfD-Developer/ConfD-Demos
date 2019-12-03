# The order of packages is significant as there are dependencies between
# the packages. Typically generated namespaces are used by other packages.
PACKAGES = drned-xmnr

all: packages ncs
.PHONY: all

packages:
	for i in $(PACKAGES); do \
		$(MAKE) -C packages/$${i}/src all || exit 1; \
	done
.PHONY: packages

ncs:
	ncs-setup --no-netsim --dest .
.PHONY: ncs

clean:
	for i in $(PACKAGES); do \
		$(MAKE) -C packages/$${i}/src clean || exit 1; \
	done
	rm -rf running.DB logs state ncs-cdb *.trace
	rm -f README.ncs README.netsim ncs.conf
	rm -rf bin
.PHONY: clean

start:
	ncs
.PHONY: start

stop:
	-ncs --stop
.PHONY: stop

reset:
	ncs-setup --reset
.PHONY: reset

cli:
	ncs_cli -C -u admin
.PHONY: cli
