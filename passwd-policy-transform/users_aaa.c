#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/poll.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <stdarg.h>
#include <stdio.h>
#include <ctype.h>

#include "confd_lib.h"
#include "confd_dp.h"
#include "confd_maapi.h"

/* include generated h file */
#include "users.h"

#define AAA_USERS   "/aaa:aaa/authentication/users"
#define AAA_GROUPS  "/nacm:nacm/groups"

int debuglevel = CONFD_SILENT;

void pval(confd_value_t *v)
{
  char buf[BUFSIZ];
  confd_pp_value(buf, BUFSIZ, v);
  fprintf(stderr, "%s\n", buf);
}

static struct confd_daemon_ctx *dctx;
static int ctlsock;
static int workersock;
struct confd_trans_cbs tcb;
struct confd_data_cbs  data;
static int maapi_socket;

struct confd_trans_validate_cbs vcb;
struct confd_valpoint_cb passwdvalp;

static void OK(int rval)
{
  if (rval != CONFD_OK) {
    fprintf(stderr, "users_aaa.c: error not CONFD_OK: %d : %s \n",
            confd_errno, confd_lasterr());
    abort();
  }
}
static int init_validation(struct confd_trans_ctx *tctx)
{
    confd_trans_set_fd(tctx, workersock);
    return CONFD_OK;
}

static int stop_validation(struct confd_trans_ctx *tctx)
{
    return CONFD_OK;
}

static int validate(struct confd_trans_ctx *tctx,
  confd_hkeypath_t *keypath,
  confd_value_t *newval)
  {
    char password[BUFSIZ];

    if(strlen(CONFD_GET_CBUFPTR(newval)) > 16) {
      confd_trans_seterr(tctx, "Length > 16");
      return CONFD_ERR;
    }
    strcpy(&password[0], CONFD_GET_CBUFPTR(newval));
    char *uppercasew = strrchr(password, 'W');
    if (uppercasew && strcmp(uppercasew, "World") == 0) {
      confd_trans_seterr(tctx, "Are you really sure you want password must end with 'World'");
      return CONFD_VALIDATION_WARN;
    } else if (uppercasew && strcmp(uppercasew, "Willy") == 0) {
      confd_trans_seterr(tctx, "The password must not end with 'Willy'");
      return CONFD_ERR;
    }
    return CONFD_OK;
  }

static int init_transformation(struct confd_trans_ctx *tctx)
{
  OK(maapi_attach(maapi_socket, 0, tctx));
  confd_trans_set_fd(tctx, workersock);
  return CONFD_OK;
}

static int stop_transformation(struct confd_trans_ctx *tctx)
{
  if (tctx->t_opaque != NULL) {
    struct maapi_cursor *mc = (struct maapi_cursor *)tctx->t_opaque;
    maapi_destroy_cursor(mc);
    free(tctx->t_opaque);
  }
  OK(maapi_detach(maapi_socket, tctx));
  return CONFD_OK;
}


static int maapi_sock(int *sock)
{
  struct sockaddr_in addr;

  addr.sin_addr.s_addr = inet_addr("127.0.0.1");
  addr.sin_family = AF_INET;
  addr.sin_port = htons(4565);

  if ((*sock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open socket\n");

  if (maapi_connect(*sock, (struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to confd \n");

  return CONFD_OK;
}

/* free all memory allocated by maapi_get_list_elem() */
static void free_list(confd_value_t *list, int n)
{
  int i;

  if (list != NULL) {
    for (i = 0; i < n; i++) {
      confd_free_value(&list[i]);
    }
    free(list);
  }
}

/* return index of user in group list, or -1 if not found */
static int get_group_member(confd_value_t *group, int n, char *user)
{
  int i;

  for (i = 0; i < n; i++) {
    if (strcmp(CONFD_GET_CBUFPTR(&group[i]), user) == 0)
      return i;
  }
  return -1;
}

static int get_elem(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *keypath)

{
  confd_value_t v;
  confd_value_t *leaf = &(keypath->v[0][0]);
  confd_value_t *vp = &(keypath->v[1][0]);

  switch (CONFD_GET_XMLTAG(leaf)) {
  case users_name:
    if (maapi_get_elem(maapi_socket, tctx->thandle, &v,
                       "%s/user{%x}/name", AAA_USERS, vp) == CONFD_OK) {
      confd_data_reply_value(tctx, &v);
      confd_free_value(&v);
      return CONFD_OK;
    }
    else if (confd_errno == CONFD_ERR_NOEXISTS) {
      confd_data_reply_not_found(tctx);
      return CONFD_OK;
    }
    else {
      printf ("errno = %d\n", confd_errno);
      return CONFD_ERR;
    }
  case users_password:
    if (maapi_get_elem(maapi_socket, tctx->thandle, &v,
                       "%s/user{%x}/password", AAA_USERS, vp) == CONFD_OK) {
      confd_data_reply_value(tctx, &v);
      confd_free_value(&v);
      return CONFD_OK;
    }
    else if (confd_errno == CONFD_ERR_NOEXISTS) {
      confd_data_reply_not_found(tctx);
      return CONFD_OK;
    }
    else {
      fprintf (stderr, "errno = %d\n", confd_errno);
      return CONFD_ERR;
    }
  case users_role: {
    char *user = CONFD_GET_CBUFPTR(vp);
    confd_value_t *users;
    int n_users;
    int index;

    index = -1;
    if (maapi_get_list_elem(
          maapi_socket, tctx->thandle, &users, &n_users,
          "%s/group{admin}/user-name", AAA_GROUPS) == CONFD_OK) {
      index = get_group_member(users, n_users, user);
      free_list(users, n_users);
    }
    if (index >= 0) {
      CONFD_SET_ENUM_VALUE(&v, users_admin);
      confd_data_reply_value(tctx, &v);
      return CONFD_OK;
    }

    index = -1;
    if (maapi_get_list_elem(
          maapi_socket, tctx->thandle, &users, &n_users,
          "%s/group{oper}/user-name", AAA_GROUPS) == CONFD_OK) {
      index = get_group_member(users, n_users, user);
      free_list(users, n_users);
    }
    if (index >= 0) {
      CONFD_SET_ENUM_VALUE(&v, users_oper);
      confd_data_reply_value(tctx, &v);
      return CONFD_OK;
    }

    /* user not part of any group at all */
    confd_data_reply_not_found(tctx);
    return CONFD_OK;
  }


  default:
    confd_fatal("Unexpected switch tag %d\n",
                CONFD_GET_XMLTAG(leaf));
  }
  return CONFD_ERR;
}


static void add_user_to_group(struct confd_trans_ctx *tctx,
                              confd_value_t *key, char *group)
{
  char *user = CONFD_GET_CBUFPTR(key);
  confd_value_t *users = NULL;
  int n_users = 0;
  int index = -1;
  confd_value_t list;

  if (maapi_get_list_elem(
        maapi_socket, tctx->thandle, &users, &n_users,
        "%s/group{%s}/user-name", AAA_GROUPS, group) == CONFD_OK) {
    index = get_group_member(users, n_users, user);
  }
  if (index < 0) {
    users = realloc(users, (n_users + 1) * sizeof(confd_value_t));
    CONFD_SET_STR(&users[n_users], user);
    CONFD_SET_LIST(&list, users, n_users + 1);
    OK(maapi_set_elem(maapi_socket, tctx->thandle, &list,
                      "%s/group{%s}/user-name", AAA_GROUPS, group));
  }
  free_list(users, n_users);
}


static void del_user_from_group(struct confd_trans_ctx *tctx,
                                confd_value_t *key, char *group)
{
  char *user = CONFD_GET_CBUFPTR(key);
  confd_value_t *users = NULL;
  int n_users = 0;
  int index = -1;
  int i;
  confd_value_t list;

  if (maapi_get_list_elem(
        maapi_socket, tctx->thandle, &users, &n_users,
        "%s/group{%s}/user-name", AAA_GROUPS, group) == CONFD_OK) {
    index = get_group_member(users, n_users, user);
  }
  if (index >= 0) {
    /* remove user and shift remaining  */
    confd_free_value(&users[index]);
    n_users--;
    for (i = index; i < n_users; i++) {
      users[i] = users[i + 1];
    }
    CONFD_SET_LIST(&list, users, n_users);
    OK(maapi_set_elem(maapi_socket, tctx->thandle, &list,
                      "%s/group{%s}/user-name", AAA_GROUPS, group));
  }
  free_list(users, n_users);
}


static int set_elem(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *keypath,
                    confd_value_t *newval)
{
  confd_value_t *leaf = &(keypath->v[0][0]);
  confd_value_t *kp = &(keypath->v[1][0]);

  switch (CONFD_GET_XMLTAG(leaf)) {
  case users_password:
    if (maapi_set_elem2(maapi_socket, tctx->thandle, CONFD_GET_CBUFPTR(newval),
                        "%s/user{%x}/password", AAA_USERS, kp) == CONFD_OK) {
      return CONFD_OK;
    }
    return CONFD_ERR;
  case users_role:
    switch CONFD_GET_ENUM_VALUE(newval) {
        case users_admin:
          OK(maapi_set_elem2(maapi_socket, tctx->thandle, "0",
                             "%s/user{%x}/uid", AAA_USERS, kp));

          OK(maapi_set_elem2(maapi_socket, tctx->thandle, "0",
                             "%s/user{%x}/gid", AAA_USERS, kp));
          add_user_to_group(tctx, kp, "admin");
          del_user_from_group(tctx, kp, "oper");
          break;
          case users_oper:
            OK(maapi_set_elem2(maapi_socket, tctx->thandle, "20",
                               "%s/user{%x}/uid", AAA_USERS, kp));

            OK(maapi_set_elem2(maapi_socket, tctx->thandle, "20",
                               "%s/user{%x}/gid", AAA_USERS, kp));
            add_user_to_group(tctx, kp, "oper");
            del_user_from_group(tctx, kp, "admin");
            break;
            default:
              confd_fatal("Unexpected switch tag %d\n",
                          CONFD_GET_ENUM_VALUE(newval));
      }
    return CONFD_OK;
  default:
    confd_fatal("Unexpected switch tag %d\n",
                CONFD_GET_XMLTAG(leaf));
  }
  return CONFD_ERR;
}


static int get_next(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *keypath,
                    long next)
{
  struct maapi_cursor *mc;

  if (next == -1) {
    /* need to create a maapi cursor */
    if (tctx->t_opaque == NULL) {
      mc = (struct maapi_cursor *)malloc(sizeof(struct maapi_cursor));
      tctx->t_opaque = mc;
    } else {
      mc = (struct maapi_cursor *)tctx->t_opaque;
      maapi_destroy_cursor(mc);
    }
    OK(maapi_init_cursor(maapi_socket, tctx->thandle, mc,
                         "%s/user", AAA_USERS));
  } else {
    mc = (struct maapi_cursor *)tctx->t_opaque;
  }

  if (maapi_get_next(mc) != CONFD_OK) {
    return CONFD_ERR;
  }

  if (mc->n == 0) {
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }
  confd_data_reply_next_key(tctx, &(mc->keys[0]), 1, 1);
  return CONFD_OK;
}


static int dbremove(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *keypath)
{
  OK(maapi_delete(maapi_socket, tctx->thandle,
                  "%s/user{%x}", AAA_USERS, &(keypath->v[0][0])));
  del_user_from_group(tctx, &(keypath->v[0][0]), "oper");
  del_user_from_group(tctx, &(keypath->v[0][0]), "admin");
  return CONFD_OK;
}



static int create(struct confd_trans_ctx *tctx,
                  confd_hkeypath_t *keypath)
{
  confd_value_t *user = &(keypath->v[0][0]);
  ssize_t bufsz =  snprintf(NULL, 0, "/var/confd/home/%s",
                            CONFD_GET_BUFPTR(user));
  char buf[bufsz + strlen("/.ssh")];

  OK(maapi_create(maapi_socket, tctx->thandle, "%s/user{%x}", AAA_USERS,
                  user));
  snprintf(buf, bufsz, "/var/confd/home/%s", CONFD_GET_BUFPTR(user));
  OK(maapi_set_elem2(maapi_socket, tctx->thandle, buf,
                     "%s/user{%x}/homedir", AAA_USERS, user));
  strcat(buf, "/.ssh");
  OK(maapi_set_elem2(maapi_socket, tctx->thandle, buf,
                     "%s/user{%x}/ssh_keydir", AAA_USERS,
                     user));
  return CONFD_OK;
}


int main(int argc, char **argv)
{
  int c;
  struct sockaddr_in addr;

  while ((c = getopt(argc, argv, "tdpsr")) != -1) {
    switch(c) {
    case 't':
      debuglevel = CONFD_TRACE;
      break;
    case 'd':
      debuglevel = CONFD_DEBUG;
      break;
    case 'p':
      debuglevel = CONFD_PROTO_TRACE;
      break;
    case 's':
      debuglevel = CONFD_SILENT;
      break;
    }
  }

  confd_init("maapi", stderr, debuglevel);

  if ((dctx = confd_init_daemon("users_aaa")) == NULL)
    confd_fatal("Failed to initialize confd\n");

  if ((ctlsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open ctlsocket\n");

  addr.sin_addr.s_addr = inet_addr("127.0.0.1");
  addr.sin_family = AF_INET;
  addr.sin_port = htons(CONFD_PORT);

  if (confd_load_schemas((struct sockaddr*)&addr,
                         sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from confd\n");

  /* Create the first control socket, all requests to */
  /* create new transactions arrive here */

  if (confd_connect(dctx, ctlsock, CONTROL_SOCKET, (struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to confd \n");


  /* Also establish a workersocket, this is the most simple */
  /* case where we have just one ctlsock and one workersock */

  if ((workersock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open workersocket\n");
  if (confd_connect(dctx, workersock, WORKER_SOCKET,(struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to confd \n");

  tcb.init = init_transformation;
  tcb.finish = stop_transformation;
  confd_register_trans_cb(dctx, &tcb);


  data.get_elem = get_elem;
  data.get_next = get_next;
  data.set_elem = set_elem;
  data.create   = create;
  data.remove   = dbremove;
  data.exists_optional = NULL;
  strcpy(data.callpoint, "simple_aaa");

  if (confd_register_data_cb(dctx, &data) == CONFD_ERR)
    confd_fatal("Failed to register data cb \n");

  vcb.init = init_validation;
  vcb.stop = stop_validation;
  confd_register_trans_validate_cb(dctx, &vcb);

  passwdvalp.validate = validate;
  strcpy(passwdvalp.valpoint, "passwdvp");
  OK(confd_register_valpoint_cb(dctx, &passwdvalp));

  OK(confd_register_done(dctx));
  OK(maapi_sock(&maapi_socket));

  while (1) {
    struct pollfd set[2];
    int ret;

    set[0].fd = ctlsock;
    set[0].events = POLLIN;
    set[0].revents = 0;

    set[1].fd = workersock;
    set[1].events = POLLIN;
    set[1].revents = 0;


    if (poll(&set[0], 2, -1) < 0) {
      perror("Poll failed:");
      continue;
    }

    if (set[0].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, ctlsock)) == CONFD_EOF) {
        confd_fatal("Control socket closed\n");
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
        confd_fatal("Error on control socket request: %s (%d): %s\n",
                    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }
    if (set[1].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, workersock)) == CONFD_EOF) {
        confd_fatal("Worker socket closed\n");
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
        confd_fatal("Error on worker socket request: %s (%d): %s\n",
                    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }

  }
}
