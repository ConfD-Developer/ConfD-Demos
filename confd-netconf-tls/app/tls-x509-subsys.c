/* This example code is placed in the public domain. */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <gnutls/gnutls.h>

#include <netinet/tcp.h>
#include <sys/poll.h>
#include <ctype.h>
#include <stdarg.h>
#include <errno.h>
#include <pwd.h>
#include <grp.h>

#define KEYFILE "x509-server-key.pem"
#define CERTFILE "x509-server.pem"
#define CAFILE "x509-ca.pem"
#define CRLFILE "crl.pem"

/* This is a sample TLS 1.2 NETCONF server, using X.509 authentication.
 */

#define SA struct sockaddr
#define SOCKET_ERR(err,s) if(err==-1) {perror(s);return(1);}
#define MAX_BUF 1024
#define PORT 6513               /* listen to 6513 port - IANA assigned NETCONF over TLS service port */
#define DH_BITS 1024

/* These are global */
gnutls_certificate_credentials_t x509_cred;
gnutls_priority_t priority_cache;

#define NETCONF_TCP_PORT 2023

static gnutls_session_t
initialize_tls_session (void)
{
  gnutls_session_t session;

  gnutls_init (&session, GNUTLS_SERVER);

  gnutls_priority_set (session, priority_cache);

  gnutls_credentials_set (session, GNUTLS_CRD_CERTIFICATE, x509_cred);

  /* request client certificate if any.
   */
  gnutls_certificate_server_set_request (session, GNUTLS_CERT_REQUEST);

  /* Set maximum compatibility mode. This is only suggested on public webservers
   * that need to trade security for compatibility
   */
  gnutls_session_enable_compatibility_mode (session);

  return session;
}

static gnutls_dh_params_t dh_params;

static int
generate_dh_params (void)
{

  /* Generate Diffie-Hellman parameters - for use with DHE
   * kx algorithms. When short bit length is used, it might
   * be wise to regenerate parameters.
   *
   * Check the ex-serv-export.c example for using static
   * parameters.
   */
  gnutls_dh_params_init (&dh_params);
  gnutls_dh_params_generate2 (dh_params, DH_BITS);

  return 0;
}

int write_fill(int fd, unsigned char *buf, int len)
{
    int i;
    unsigned int done = 0;

    do {
        if ((i = write(fd, (char *)(buf+done), len-done)) < 0) {
            if (errno != EINTR)
                return (i);
            i = 0;
        }
        done += i;
    } while (done < len);
    return (len);
}

int
main (void)
{
  int err, listen_sd;
  int sd, ret;
  struct sockaddr_in sa_serv;
  struct sockaddr_in sa_cli;
  unsigned int client_len;
  char topbuf[512];
  gnutls_session_t session;
  char buffer[MAX_BUF + 1];
  int optval = 1;

  struct sockaddr_in sa_confd;
  int confd_sd;
  struct pollfd fds[2];
  int nfds = 2;
  int one = 1;
  
  /* this must be called once in the program
   */
  gnutls_global_init ();

  /* Set server credentials */ 
  gnutls_certificate_allocate_credentials (&x509_cred);
  gnutls_certificate_set_x509_trust_file (x509_cred, CAFILE,
                                          GNUTLS_X509_FMT_PEM);

  gnutls_certificate_set_x509_crl_file (x509_cred, CRLFILE,
                                        GNUTLS_X509_FMT_PEM);

  gnutls_certificate_set_x509_key_file (x509_cred, CERTFILE, KEYFILE,
                                        GNUTLS_X509_FMT_PEM);

  generate_dh_params ();

  gnutls_priority_init (&priority_cache, "NORMAL", NULL);

  gnutls_certificate_set_dh_params (x509_cred, dh_params);

  /* Socket operations
   */
  listen_sd = socket (AF_INET, SOCK_STREAM, 0);
  SOCKET_ERR (listen_sd, "socket");

  memset (&sa_serv, '\0', sizeof (sa_serv));
  sa_serv.sin_family = AF_INET;
  sa_serv.sin_addr.s_addr = INADDR_ANY;
  sa_serv.sin_port = htons (PORT);      /* Server Port number */

  setsockopt (listen_sd, SOL_SOCKET, SO_REUSEADDR, (void *) &optval,
              sizeof (int));

  err = bind (listen_sd, (SA *) & sa_serv, sizeof (sa_serv));
  SOCKET_ERR (err, "bind");
  err = listen (listen_sd, 1024);
  SOCKET_ERR (err, "listen");

  printf ("Server ready. Listening to port '%d'.\n\n", PORT);
  daemon(1,1);
  
  client_len = sizeof (sa_cli);
  for (;;) {
    session = initialize_tls_session ();

    sd = accept (listen_sd, (SA *) & sa_cli, &client_len);

    printf ("- connection from %s, port %d\n",
	    inet_ntop (AF_INET, &sa_cli.sin_addr, topbuf,
		       sizeof (topbuf)), ntohs (sa_cli.sin_port));

    gnutls_transport_set_ptr (session, (gnutls_transport_ptr_t ) sd);
    ret = gnutls_handshake (session);
    if (ret < 0)
      {
	close (sd);
	gnutls_deinit (session);
	fprintf (stderr, "*** Handshake has failed (%s)\n\n",
		 gnutls_strerror (ret));
	continue;
      }
    printf ("- Handshake was completed\n");

    if ((confd_sd = socket(PF_INET, SOCK_STREAM, 0)) < 0 ) {
      fprintf(stderr, "Failed to open ConfD ctlsocket\n");
      break;
    }

    sa_confd.sin_addr.s_addr = inet_addr("127.0.0.1");
    sa_confd.sin_family = AF_INET;
    sa_confd.sin_port = htons(NETCONF_TCP_PORT);

    if (connect(confd_sd,  (struct sockaddr*)&sa_confd,
                sizeof (struct sockaddr_in)) < 0) {
      fprintf(stderr, "Failed to connect to ConfD\n");
      break;
    }

    (void)setsockopt(confd_sd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

    /* Now we need to tell ConfD who we are */
    /* Note that we greatly simplified the client identity in this example by assuming that only the 
       admin user from the 1-2-3 ConfD intro example hold a valid client certificate. Real implementations will 
       need to verify the client identity according to section 7 of RFC7589 */

    sprintf(buffer, "[%s;%s/%d;ssh;%d;%d;%s;%s;;]\n",
	    "admin", topbuf, ntohs (sa_cli.sin_port),
	    9000, 100,
	    "", "/var/confd/homes/admin");
      
    write(confd_sd, buffer, strlen(buffer));
     
    /* Setup poll */ 
    fds[0].fd = confd_sd;
    fds[0].events = POLLIN;
    fds[1].fd = sd;
    fds[1].events = POLLIN;

    for (;;) {
      fds[0].revents = 0;
      fds[1].revents = 0;
      memset (buffer, 0, MAX_BUF + 1);
	
      if (poll(&fds[0], nfds, -1) < 0) {
	perror("Poll failed:");
	continue;
      }
	
      /* Check for I/O */
      if (fds[1].revents & (POLLIN | POLLHUP)) {
	ret = gnutls_record_recv (session, buffer, MAX_BUF);
	if (ret == 0) {
	  printf ("\n- Peer has closed the GnuTLS connection\n");
	  break;
	}
	else if (ret < 0) {
	  fprintf (stderr, "\n*** Received corrupted "
		   "data(%d). Closing the connection.\n\n", ret);
	  break;
	}
	else if (ret > 0) {
	  /* forward data to the NETCONF server */
	  if (write_fill(confd_sd, buffer, ret) != ret) {
	    fprintf(stderr, "Failed to write to the ConfD NETCONF server on fd %d: %d\n", confd_sd, errno);
	    break;
	  }
	}
      }
      else if (fds[1].revents) {
	fprintf(stderr, "Poll error from TLS client\n");
	break;
      }
      else if (fds[0].revents & (POLLIN | POLLHUP)) {
	if ((ret = read(confd_sd, buffer, MAX_BUF)) == 0) {
	  /* eof from NETCONF server - we're done */
	  break;
	}
	if (ret < 0) {
	  fprintf(stderr, "Failed to read on fd %d: %d\n", confd_sd, errno);
	  break;
	}
	gnutls_record_send (session, buffer, strlen (buffer));
      }
      else if (fds[0].revents) {
	fprintf(stderr, "Poll error from server\n");
	break;
      }
    }
    printf ("\n");
    /* do not wait for the peer to close the connection.
     */
    gnutls_bye (session, GNUTLS_SHUT_WR);

    close (sd);
    gnutls_deinit (session);

  }
  close (listen_sd);

  gnutls_certificate_free_credentials (x509_cred);
  gnutls_priority_deinit (priority_cache);

  gnutls_global_deinit ();

  return 0;

}
