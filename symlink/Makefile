include $(CONFD_DIR)/src/confd/build/include.mk

all: symlinked.fxs root.fxs transform

symlinked.fxs: root.yang

%.fxs: %.yang
	$(CONFDC) -c -o $@ $<

%.h: %.fxs
	$(CONFDC) --emit-h $@ $<

T_LOGLEVEL ?= T_LOG_INFO

transform: transform.c symlinked.h
	$(CC) -o $@ -D$(T_LOGLEVEL) -I $(CONFD_DIR)/examples.confd/include -I $(CONFD_DIR)/include $< $(LIBS)

start: start_confd
	./transform

start_confd: stop dirs
	$(CONFD) -c confd.conf --addloadpath $(CONFD_DIR)/etc/confd

.PHONY: dirs

dirs: ssh-keydir $(CDB_DIR) logs

logs:
	mkdir -p $@

stop:
	-pkill -x transform
	-$(CONFD) --stop

clean: iclean
	rm -f transform symlinked.h
	rm -rf logs
