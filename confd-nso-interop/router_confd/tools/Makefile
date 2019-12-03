LIBCONFD  = $(CONFD_DIR)/lib/libconfd.a
CFLAGS   += -Wall -g -I../ipc_drv -I$(CONFD_DIR)/include

LDFLAGS    = -lpthread
LDFLAGS   += -ldl

all: confd_cmd

confd_cmd: confd_cmd.c
	$(CC) -o $@ $< $(CFLAGS) $(LIBCONFD) $(LDFLAGS) -lm

clean:
	rm -f *.o a.out core confd_cmd
	rm -rf *.dSYM
