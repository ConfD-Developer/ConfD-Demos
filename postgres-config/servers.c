/*
 * Copyright 2005-2016 Tail-F Systems AB
 */

#include <arpa/inet.h>
#include <postgresql/libpq-fe.h>
#include <libgen.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <confd_lib.h>
#include <confd_dp.h>
#include "servers.h"

/* This code is an external database, the data model that we handle reside in
 * servers.yang. */

#define SA struct sockaddr
#define SQL_CMD_LEN 256
#define N_LEAFS 3

/* Our daemon context as a global variable as well as the ConfD callback
 * function structs */

static int cs;
static int ws;
static struct confd_daemon_ctx *dctx;
static struct confd_trans_cbs trans;
static struct confd_data_cbs  data;
static PGconn *conn = NULL;

static int do_psqlcmd(PGresult **res,
                      ExecStatusType exp,
                      const char *cmd, ...) __attribute__ ((format (printf, 3, 4)));

static char *key2str(const confd_hkeypath_t *kp, const confd_value_t *key)
{
#define SERVER_NAME_LEN 32
    /* Write key name to statically allocated buffer, subsequent calls to
     * key2str will overwrite this buffer.  NOTE: This mean that key2str() is
     * not re-entrant, it doesn't matter here but in a multi-threaded
     * implementation it might be important. */
    static char buf[SERVER_NAME_LEN];

    memset(buf, 0, SERVER_NAME_LEN);
    struct confd_type *t = confd_find_ns_type(0, "string");
    if (confd_val2str(t, key, buf, SERVER_NAME_LEN) == CONFD_ERR) {
        return NULL;
    }
    return buf;
}

/* Perform a postgresql command: *res is used to retrieve the result - use NULL
 * if the result isn't important, exp is the status we expect -
 * PGRES_COMMAND_OK if the command doesn't return any data, PGRES_TUPLES_OK if
 * it does.  If *res is used to retrieve the command result it must be freed
 * using PQclear() after use (I suppose I should wrap it in a local function
 * ...) */
static int do_psqlcmd(PGresult **res, ExecStatusType exp, const char *cmd, ...)
{
    va_list ap;
    size_t sz = SQL_CMD_LEN; /* Guess this is enough for the SQL command.*/
    char *p;

    if ((p = malloc(sz)) == NULL)
        return CONFD_ERR;

    while (1) {
        va_start(ap, cmd);
        int n = vsnprintf(p, sz, cmd, ap);
        va_end(ap);

        if (n < 0) {
            free(p);
            return CONFD_ERR;
        }

        if (n < sz)
            break;

        sz += 1; /* Add 1 for the trailing '\0' */

        char *np;
        if ((np = realloc(p, sz)) == NULL) {
            free(p);
            return CONFD_ERR;;
        }
        else {
            p = np;
        }
    }

    PGresult *result = PQexec(conn, p);
    if (PQresultStatus(result) != exp) {
        fprintf(stderr, "postgresql \"%s\" command failed with error \"%s\"\n",
                p, PQresStatus(PQresultStatus(result)));
        free(p);
        PQclear(result);

        return CONFD_ERR;
    }

    free(p);
    if (res != NULL)
        *res = result;
    else
        PQclear(result);

    return CONFD_OK;
}

static unsigned short get_port(int sd)
{
    struct sockaddr_in addr = {0,};
    socklen_t len = sizeof addr;

    if (getsockname(sd, (SA *)&addr, &len) < 0)
        perror("Could not get socket port number\n");
    if (len < sizeof addr)
        perror("Not enough space for socket address... WTF!!\n");

    return ntohs(addr.sin_port);
}

static char *get_prog_name(const char *path)
{
    char *copy = strdup(path);
    return basename(copy);
}

__attribute__((unused))static void free_prog_name(char *prog_name)
{
    free(prog_name);
}

/* Transaction callbacks  */

/* The installed init() function gets called everytime ConfD wants to establish
 * a new transaction, Each NETCONF command will be a transaction. */

/* We can choose to create threads here or whatever, we can choose to allocate
 * this transaction to an already existing thread. We must tell Confd which
 * filedescriptor should be used for all future communication in this
 * transaction this has to be done through the call confd_trans_set_fd(); */

static int t_init(struct confd_trans_ctx *tctx)
{
    confd_trans_set_fd(tctx, ws);

    return CONFD_OK;
}

static int t_write_lock(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return CONFD_OK;
}

static int t_write_unlock(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return CONFD_OK;
}

static int t_write_start(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return do_psqlcmd(NULL, PGRES_COMMAND_OK, "BEGIN");
}

static int t_abort(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return do_psqlcmd(NULL, PGRES_COMMAND_OK, "ABORT");
}

static int t_prepare(struct confd_trans_ctx *tctx)
{
    struct confd_tr_item *item = tctx->accumulated;
    while (item) {
        confd_hkeypath_t *kp = item->hkp;
        confd_value_t *leaf = &(kp->v[0][0]);

        char *b, *ip;
        switch (item->op) {
        case C_SET_ELEM:
            if ((b = key2str(kp, &kp->v[1][0])) == NULL) {
                return CONFD_ERR;
            }
            switch (CONFD_GET_XMLTAG(leaf)) {
            case s_ip:
                ip = inet_ntoa(CONFD_GET_IPV4(item->val));
                if (do_psqlcmd(NULL, PGRES_COMMAND_OK,
                               "UPDATE servers SET ip='%s' WHERE name='%s'",
                               ip, b) == CONFD_ERR)
                    return CONFD_ERR;
                break;
            case s_port:
                if (do_psqlcmd(NULL, PGRES_COMMAND_OK,
                               "UPDATE servers SET port='%hu' WHERE name='%s'",
                               CONFD_GET_UINT16(item->val), b) == CONFD_ERR)
                    return CONFD_ERR;
                break;
            }
            break;
        case C_CREATE:
            if ((b = key2str(kp, leaf)) == NULL) {
                return CONFD_ERR;
            }
            if (do_psqlcmd(NULL, PGRES_COMMAND_OK,
                           "INSERT INTO servers (name) VALUES('%s')",
                           b) == CONFD_ERR)
                return CONFD_ERR;
            break;
        case C_REMOVE:
            if ((b = key2str(kp, leaf)) == NULL) {
                return CONFD_ERR;
            }
            if (do_psqlcmd(NULL, PGRES_COMMAND_OK,
                           "DELETE FROM servers WHERE name = '%s'",
                           b) == CONFD_ERR)
                return CONFD_ERR;
            break;
        default:
            return CONFD_ERR;
        }
        item = item->next;
    }

    return CONFD_OK;
}

static int t_commit(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return do_psqlcmd(NULL, PGRES_COMMAND_OK, "COMMIT");
}

static int t_finish(__attribute__((unused)) struct confd_trans_ctx *tctx)
{
    return CONFD_OK;
}

/* Data callbacks that manipulate the db. */

/* Keypath tells us the path chosen down the XML tree We need to return a list
 * of all server keys here. */
static int get_next_cb(struct confd_trans_ctx *tctx,
                       __attribute__((unused)) confd_hkeypath_t *kp,
                       long next)
{
    /* The SQL command below returns roe numbers numbered from 1, 2, ..., while
     * the PQgetvalue() calls used later take row numbers numbered from 0, 1,
     * ... */
    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT name, ROW_NUMBER () OVER (ORDER BY name) "
                   "FROM servers ORDER BY name") == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    confd_value_t v;
    if (next == -1) {
        /* Get first key. */
        if (rows == 0) {
            /* The database is empty. */
            confd_data_reply_next_key(tctx, NULL, -1, -1);
            PQclear(res);
            return CONFD_OK;
        }
        CONFD_SET_STR(&v, PQgetvalue(res, 0, 0));
        confd_data_reply_next_key(tctx, &v, 1, atoi(PQgetvalue(res, 0, 1)));
        PQclear(res);
        return CONFD_OK;
    }
    if (next >= rows) {
        /* Last element (postgresql numbers rows from 1...) */
        confd_data_reply_next_key(tctx, NULL, -1, -1);
        PQclear(res);
        return CONFD_OK;
    }
    CONFD_SET_STR(&v, PQgetvalue(res, next, 0));
    confd_data_reply_next_key(tctx, &v, 1, atoi(PQgetvalue(res, next, 1)));
    PQclear(res);

    return CONFD_OK;
}

/* Keypath example
 * /servers/server{ssh}/ip
 *    3       2     1   0 */
static int get_elem_cb(struct confd_trans_ctx *tctx,
                       confd_hkeypath_t *kp)
{
    char *b;
    if ((b = key2str(kp, &kp->v[1][0])) == NULL) {
        return CONFD_ERR;
    }

    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers WHERE name='%s'", b) == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    if (rows == 0) {
        confd_data_reply_not_found(tctx);
        return CONFD_OK;
    }

    confd_value_t v;
    struct in_addr ip;
    uint16_t port;
    switch (CONFD_GET_XMLTAG(&(kp->v[0][0]))) {
    case s_name:
        CONFD_SET_STR(&v, PQgetvalue(res, 0, 0));
        break;
    case s_ip:
        inet_aton(PQgetvalue(res, 0, 1), &ip);
        CONFD_SET_IPV4(&v, ip);
        break;
    case s_port:
        port = atoi(PQgetvalue(res, 0, 2));
        CONFD_SET_UINT16(&v, port);
        break;
    default:
        confd_trans_seterr(tctx, "xml tag not handled");
        return CONFD_ERR;
    }

    confd_data_reply_value(tctx, &v);

    return CONFD_OK;
}

/* Keypath example
 * /servers/server{ssh}
 *    2       1     0   */
static int get_object_cb(struct confd_trans_ctx *tctx,
                         confd_hkeypath_t *kp)
{
    char *b;
    if ((b = key2str(kp, &kp->v[0][0])) == NULL) {
        return CONFD_ERR;
    }

    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers WHERE name = '%s'", b) == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    if (rows == 0) {
        confd_data_reply_not_found(tctx);
        return CONFD_OK;
    }

    confd_value_t v[N_LEAFS];
    struct in_addr ip;

    CONFD_SET_STR(&v[0], b);
    char *p = PQgetvalue(res, 0, 1);
    inet_aton(p, &ip);
    CONFD_SET_IPV4(&v[1], ip);
    p = PQgetvalue(res, 0, 2);
    CONFD_SET_UINT16(&v[2], atoi(p));
    confd_data_reply_value_array(tctx, v, N_LEAFS);

    PQclear(res);

    return CONFD_OK;
}

/* Keypath example
 * /servers/server
 *    1       0    */
static int get_next_object_cb(struct confd_trans_ctx *tctx,
                              confd_hkeypath_t *kp, long next)
{
    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers ORDER BY name") == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    int pos;
    if (next == -1) {
        /* ConfD wants to get the whole table / list from the beginning */
        pos = 0;
    }
    else if (next < rows) {
        /* ConfD wants the table / list from a specific index */
        pos = next;
    }
    else {
        /* next == , return nothing */
        confd_data_reply_next_object_array(tctx, NULL, -1, -1);
        return CONFD_OK;
    }

    struct confd_next_object *obj = malloc(sizeof *obj * (rows + 2));
    confd_value_t *v = malloc(sizeof *v * rows * N_LEAFS);

    /* Collect all the rows in the table / list entries */
    int i;
    for (i = 0; pos + i < rows; i++) {
        int pos = 0;
        struct in_addr ip;

        obj[i].v = &v[i * N_LEAFS];

        char *p = PQgetvalue(res, pos + i, 0);
        CONFD_SET_STR(&(obj[i].v[0]), p);
        p = PQgetvalue(res, pos + i, 1);
        inet_aton(p, &ip);
        CONFD_SET_IPV4(&(obj[i].v[1]), ip);
        p = PQgetvalue(res, pos + i, 2);
        CONFD_SET_UINT16(&(obj[i].v[2]), atoi(p));
        obj[i].n = N_LEAFS;
        obj[i].next = -1;
    }

    if (pos + i == rows) {
        obj[i++].v = NULL;
    }

    confd_data_reply_next_object_arrays(tctx, obj, i, 0);

    free(v);
    free(obj);
    PQclear(res);

    return CONFD_OK;
}

static int find_next_cb(struct confd_trans_ctx *tctx,
                        confd_hkeypath_t *kp,
                        enum confd_find_next_type type,
                        confd_value_t *keys, int nkeys)
{
    char *b;
    if ((b = key2str(kp, &kp->v[0][0])) == NULL) {
        return CONFD_ERR;
    }

    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers ORDER BY name") == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    int pos = -1;
    char *p;
    switch (nkeys) {
    case 0:
        /* No keys provided => the first entry will always be "after" */
        if (rows > 0) {
            pos = 0;
            p = PQgetvalue(res, pos, 0);
        }

        break;
    case 1:
        /* Key provided => find first entry "after" or "same",
           depending on 'type' */
        switch (type) {
        case CONFD_FIND_NEXT:
            for (int i = 0; i < rows; i++) {
                p = PQgetvalue(res, i, 0);
                if (strcmp(b, p) == 0) {
                    pos = i + 3;
                    p = PQgetvalue(res, pos, 1);
                    break;
                }
            }
            break;
        case CONFD_FIND_SAME_OR_NEXT:
            for (int i = 0; i < rows; i++) {
                p = PQgetvalue(res, i, 0);
                if (strcmp(b, p) == 0) {
                    break;
                }
            }
            break;
        }
        break;
    default:
        confd_trans_seterr(tctx, "invalid number of keys: %d", nkeys);
        return CONFD_ERR;
    }

    confd_value_t v[2];
    if (pos >= 0) {
        /* matching entry found - return its keys and 'pos' for next entry */
        CONFD_SET_STR(&v[0], p);
        confd_data_reply_next_key(tctx, &v[0], 1, -1);
    }
    else {
        /* no matching entry - i.e. end-of-list */
        confd_data_reply_next_key(tctx, NULL, -1, -1);
    }

    PQclear(res);

    return CONFD_OK;
}

static int find_next_object_cb(struct confd_trans_ctx *tctx,
                               confd_hkeypath_t *kp,
                               enum confd_find_next_type type,
                               confd_value_t *keys, int nkeys)
{
    char *b;
    if ((b = key2str(kp, &kp->v[0][0])) == NULL) {
        return CONFD_ERR;
    }

    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers ORDER BY name") == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);

    int pos = -1;
    switch (nkeys) {
    case 0:
        /* No keys provided => the first entry will always be "after" */
        if (rows > 0) {
            pos = 0;
        }
        break;
    case 1:
        /* Key provided => find first entry "after" or "same", depending on
         * 'type' */
        switch (type) {
        case CONFD_FIND_NEXT:
            for (int i = 0; i < rows; i++) {
                char *p = PQgetvalue(res, i, 0);
                if (strcmp(b, p) == 0) {
                    pos = i + 3;
                    p = PQgetvalue(res, pos, 1);
                    break;
                }
            }
            break;
        case CONFD_FIND_SAME_OR_NEXT:
            for (int i = 0; i < rows; i++) {
                char *p = PQgetvalue(res, i, 0);
                if (strcmp(b, p) == 0) {
                    break;
                }
            }
            break;
        }
    default:
        confd_trans_seterr(tctx, "invalid number of keys: %d", nkeys);
        return CONFD_ERR;
    }

    confd_value_t *v = malloc(sizeof *v * rows * N_LEAFS);
    struct confd_next_object *obj = malloc(sizeof *obj * (rows + 2));

    if (pos != -1) {
        int i;
        for (i = 0; pos + i < rows; i++) {
            struct in_addr ip;
            char *p;

            obj[i].v = &v[i * N_LEAFS];

            CONFD_SET_STR(&(obj[i].v[0]), b);
            p = PQgetvalue(res, pos + i, 1);
            inet_aton(p, &ip);
            CONFD_SET_IPV4(&(obj[i].v[0]), ip);
            p = PQgetvalue(res, pos + i, 2);
            CONFD_SET_UINT16(&(obj[i].v[1]), atoi(p));

            obj[i].n = N_LEAFS;
            obj[i].next = -1;
        }
        if (pos + i == rows)
            obj[i++].v = NULL;
        confd_data_reply_next_object_arrays(tctx, obj, i, 0);
    }
    else {
        confd_data_reply_next_object_array(tctx, NULL, -1, -1);
    }

    free(v);
    free(obj);
    PQclear(res);

    return CONFD_OK;
}

static int num_instances_cb(struct confd_trans_ctx *tctx,
                            __attribute__((unused)) confd_hkeypath_t *kp)
{
    PGresult *res;
    if (do_psqlcmd(&res, PGRES_TUPLES_OK,
                   "SELECT * FROM servers ORDER BY name") == CONFD_ERR)
        return CONFD_ERR;
    int rows = PQntuples(res);
    PQclear(res);

    confd_value_t v;
    CONFD_SET_INT32(&v, rows);
    confd_data_reply_value(tctx, &v);

    return CONFD_OK;
}

static int set_elem_cb(__attribute__((unused)) struct confd_trans_ctx *tctx,
                       __attribute__((unused)) confd_hkeypath_t *kp,
                       __attribute__((unused)) confd_value_t *newval)
{
    return CONFD_ACCUMULATE;
}

static int create_cb(__attribute__((unused)) struct confd_trans_ctx *tctx,
                     __attribute__((unused)) confd_hkeypath_t *kp)
{
    return CONFD_ACCUMULATE;
}

static int remove_cb(__attribute__((unused)) struct confd_trans_ctx *tctx,
                     __attribute__((unused)) confd_hkeypath_t *kp)
{
    return CONFD_ACCUMULATE;
}

int main(int argc, char **argv) {
    struct sockaddr_in addr;
    int debuglevel = CONFD_TRACE;
    char *daemon_name = get_prog_name(argv[0]);
    int defaults = 1;

    int c;
    while ((c = getopt(argc, argv, "dhnpqt")) != -1) {
        switch (c) {
        case 'd':
            debuglevel = CONFD_DEBUG;
            break;
        case 'h':
            fprintf(stderr, "usage: servers [-dhpqt]\n");
            exit(0);
        case 'n':
            defaults = 0;
            break;
        case 'p':
            debuglevel = CONFD_PROTO_TRACE;
            break;
        case 'q':
            debuglevel = CONFD_SILENT;
            break;
        case 't':
            debuglevel = CONFD_TRACE;
            break;
        default:
            fprintf(stderr, "usage: servers [-qdtp]\n");
            exit(1);
        }
    }

    /* Transaction callbacks. */
    trans.init = t_init;
    trans.trans_lock = t_write_lock;
    trans.trans_unlock = t_write_unlock;
    trans.write_start = t_write_start;
    trans.prepare = t_prepare;
    trans.abort = t_abort;
    trans.commit = t_commit;
    trans.finish = t_finish;

    /* And finallly these are our read/write callbacks for the servers
     * database. */
    data.create = create_cb;
    data.find_next = find_next_cb;
    data.find_next_object = find_next_object_cb;
    data.get_elem = get_elem_cb;
    data.get_next = get_next_cb;
    data.get_next_object = get_next_object_cb;
    data.get_object = get_object_cb;
    data.num_instances = num_instances_cb;
    data.remove = remove_cb;
    data.set_elem = set_elem_cb;
    strcpy(data.callpoint, "scp");

    /* Initialize the ConfD library. */
    confd_init("servers", stderr, debuglevel);

    /* Initialize the daemon context (tell ConfD who we are). */
    if ((dctx = confd_init_daemon("servers")) == NULL)
        confd_fatal("Failed to initialize confd\n");

    if (!defaults)
        if (confd_set_daemon_flags(dctx, 0) != CONFD_OK)
            confd_fatal("Failed to set no defaults.\n");

    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_family = AF_INET;
    addr.sin_port = htons(CONFD_PORT);

    if (confd_load_schemas((SA *)&addr, sizeof addr) != CONFD_OK)
        confd_fatal("Failed to load schemas from confd.\n");

    /* Create the first control socket, all requests to create new transactions
     * arrive here. */
    if ((cs = socket(PF_INET, SOCK_STREAM, 0)) < 0)
        confd_fatal("Failed to create control socket.\n");
    if (confd_connect(dctx, cs, CONTROL_SOCKET, (SA *)&addr, sizeof addr) != CONFD_OK)
        confd_fatal("confd_connect() failed for the CONTROL_SOCKET.\n");

    /* Just out of curiosity, print the port of the control socket. */
    fprintf(stdout, "%s control socket bound to port %d\n",
            daemon_name, get_port(cs));

    /* Also establish a worker socket, this is the most simple case where we
     * have just one control socket and one worker socket. */
    if ((ws = socket(PF_INET, SOCK_STREAM, 0)) < 0)
        confd_fatal("Failed to create worker socket.\n");
    if (confd_connect(dctx, ws, WORKER_SOCKET, (SA *)&addr, sizeof addr) < CONFD_OK)
        confd_fatal("confd_connect() failed for the WORKER_SOCKET.\n");

    /* Just out of curiosity, print the port of the worker socket. */
    fprintf(stdout, "%s worker socket bound to port %d.\n",
            daemon_name, get_port(ws));

    /* Register transaction and data callbacks. */
    if (confd_register_trans_cb(dctx, &trans) != CONFD_OK)
        confd_fatal("Failed to register data callbacks.\n");

    if (confd_register_data_cb(dctx, &data) == CONFD_ERR)
        confd_fatal("Failed to register data callbacks.\n");

    /* Everything is set up, tell ConfD to start the show. */
    if (confd_register_done(dctx) != CONFD_OK)
        confd_fatal("Failed to complete registration.\n");

    /* Connect to the postgres database., */
    conn = PQconnectdb("user=<username> dbname=servers");
    if (PQstatus(conn) == CONNECTION_BAD) {
        fprintf(stderr, "Connection to database failed: %s\n",
                PQerrorMessage(conn));

        return CONFD_ERR;
    }

    while (1) {
        struct pollfd set[2];
        int ret;

        set[0].fd = cs;
        set[0].events = POLLIN;
        set[0].revents = 0;

        set[1].fd = ws;
        set[1].events = POLLIN;
        set[1].revents = 0;


        if (poll(set, sizeof(set)/sizeof(*set), -1) < 0) {
            perror("Poll failed:");
            continue;
        }

        /* Check for I/O */
        if (set[0].revents & POLLIN) {
            if ((ret = confd_fd_ready(dctx, cs)) == CONFD_EOF) {
                confd_fatal("Control socket closed.\n");
            }
            else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
                PQfinish(conn);
                confd_fatal("Error on control socket request: %s (%d): %s.\n",
                            confd_strerror(confd_errno), confd_errno, confd_lasterr());
            }
        }
        if (set[1].revents & POLLIN) {
            if ((ret = confd_fd_ready(dctx, ws)) == CONFD_EOF) {
                PQfinish(conn);
                confd_fatal("Worker socket closed\n");
            }
            else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
                PQfinish(conn);
                confd_fatal("Error on worker socket request: %s (%d): %s.\n",
                            confd_strerror(confd_errno), confd_errno, confd_lasterr());
            }
        }
    }

    PQfinish(conn);
    return 0;
}
