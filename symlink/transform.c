#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <confd_lib.h>
#include <confd_dp.h>
#include <confd_maapi.h>

#define _TRACE_DECLARE
#include <traceh.h>

#include "symlinked.h"

#define DAMEON_NAME_STR "transform"

int maapisock, workersock, ctlsock;

struct traversal_data {
    int traversal_id;
    struct maapi_cursor mc;
    struct traversal_data *next;
};

struct prefix_map {
    char *from, *to;
};

struct prefix_map_list {
    int len;
    struct prefix_map maps[];
} prefix_maps = {.maps = {{.from = "/web-service/servers/server", .to = "/server"}},
                 .len = 1};

struct sockaddr_in get_sockaddr_by_ip_port(in_addr_t addr, in_port_t port)
{
    struct sockaddr_in sock_addr;
    sock_addr.sin_addr.s_addr = addr;
    sock_addr.sin_family = AF_INET;
    sock_addr.sin_port = htons(port);
    return sock_addr;
}

int confd_sock_init(in_addr_t addr, in_port_t port, struct confd_daemon_ctx *dctx,
                    enum confd_sock_type type)
{
    struct sockaddr_in dest_addr = get_sockaddr_by_ip_port(addr, port);
    int sock = socket(PF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        confd_fatal("Failed to open socket\n");
    }
    int res = confd_connect(dctx, sock, type,
                            (struct sockaddr*)&dest_addr, sizeof (struct sockaddr_in));
    if (res < 0) {
        confd_fatal("Failed to confd_connect() to confd \n");
    }
    return sock;
}

int maapi_sock_init(in_addr_t addr, in_port_t port)
{
    struct sockaddr_in dest_addr = get_sockaddr_by_ip_port(addr, port);
    int sock = socket(PF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        confd_fatal("Failed to open MAAPI socket\n");
    }
    int res = maapi_connect(sock, (struct sockaddr*)&dest_addr,
                            sizeof (struct sockaddr_in));
    if (res < 0) {
        confd_fatal("Failed to maapi_connect() to confd \n");
    }
    return sock;
}

static int get_debug_level(int argc, char **argv)
{
    int debuglevel = CONFD_DEBUG;
    int c;
    while ((c = getopt(argc, argv, "tdps")) != -1) {
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
    return debuglevel;
}

struct traversal_data *free_traversal_data(struct traversal_data *start, int traversal_id)
{
    struct traversal_data *p, *td;
    for (p = td = start; td != NULL; td = td->next) {
        if (td->traversal_id == traversal_id) {
            break;
        }
        p = td;
    }
    if (td == NULL) {
        return start;
    }
    if (td == start) {
        start = start->next;
    }
    p->next = td->next;
    maapi_destroy_cursor(&td->mc);
    free(td);
    return start;
}

/* Lookup the symlink source path based on the kp prefix.  It is
   somewhat frail as it assumes exactly the same path coding. */
int translate_path(confd_hkeypath_t *kp, char *target_path)
{
    char path[BUFSIZ];
    confd_pp_kpath(path, BUFSIZ, kp);
    int found = 0;
    struct prefix_map *map;
    for (int i = 0; i < prefix_maps.len; i++) {
        map = &prefix_maps.maps[i];
        if (strncmp(path, map->from, strlen(map->from)) == 0) {
            found = 1;
            break;
        }
    }
    if (! found) {
        WARN("failed to match path to translate: %s", path);
        return CONFD_ERR;
    }
    if (snprintf(target_path, BUFSIZ, "%s%s", map->to, path + strlen(map->from)) >= BUFSIZ) {
        WARN("target path too long");
        return CONFD_ERR;
    }
    TRACE("translated path %s -> %s", path, target_path);
    return CONFD_OK;
}

/* transaction callbacks */

static int init_transformation(struct confd_trans_ctx *tctx)
{
    TRACE_ENTER("");
    // attach to the current transaction to have access to transaction
    // data
    if (maapi_attach(maapisock, 0, tctx) != CONFD_OK) {
        confd_fatal("failed to attach to the maapi socket");
    }
    tctx->t_opaque = NULL;
    confd_trans_set_fd(tctx, workersock);
    TRACE_EXIT("");
    return CONFD_OK;
}

static int finish_transformation(struct confd_trans_ctx *tctx)
{
    struct traversal_data *td = (struct traversal_data*) tctx->t_opaque, *p;
    while (td != NULL) {
        p = td->next;
        maapi_destroy_cursor(&td->mc);
        free(td);
        td = p;
    }
}

/* Transform callbacks */

#define CHECK(call, msg, ...) do                \
        if ((call) != CONFD_OK) {               \
            WARN(msg, ##__VA_ARGS__);           \
            return CONFD_ERR;                   \
        } while(0)

static int cb_exists_optional(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp)
{
    char target_path[BUFSIZ];
    CHECK(translate_path(kp, target_path), "failed to translate path");
    if (maapi_exists(maapisock, tctx->thandle, "%s", target_path)) {
        confd_data_reply_found(tctx);
    } else {
        confd_data_reply_not_found(tctx);
    }
    return CONFD_OK;
}

static int cb_get_elem(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp)
{
    char target_path[BUFSIZ];
    confd_value_t v;
    CHECK(translate_path(kp, target_path), "failed to translate path");
    if (maapi_get_elem(maapisock, tctx->thandle, &v, "%s", target_path) == CONFD_ERR) {
        if (confd_errno != CONFD_ERR_NOEXISTS) {
            WARN("get_elem failed");
            return CONFD_ERR;
        }
        // this might be perfectly legal
        confd_data_reply_not_found(tctx);
    } else {
        confd_data_reply_value(tctx, &v);
        confd_free_value(&v);
    }
    return CONFD_OK;
}

static int cb_get_next(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp, long next)
{
    struct maapi_cursor *mc;
    if (next == -1) {
        // need to allocate another traversal data
        char target_path[BUFSIZ];
        CHECK(translate_path(kp, target_path), "failed to translate path");
        struct traversal_data *td = malloc(sizeof(*td));
        td->next = (struct traversal_data*) tctx->t_opaque;
        tctx->t_opaque = td;
        td->traversal_id = tctx->traversal_id;
        mc = &td->mc;
        maapi_init_cursor(maapisock, tctx->thandle, mc, "%s", target_path);
    } else {
        mc = (struct maapi_cursor*) next;
    }
    maapi_get_next(mc);
    if (mc->n == 0) {
        confd_data_reply_next_key(tctx, NULL, 0, 0);
        tctx->t_opaque = free_traversal_data((struct traversal_data*)tctx->t_opaque,
                                             tctx->traversal_id);
    } else {
        confd_data_reply_next_key(tctx, mc->keys, mc->n, (long) mc);
    }
    return CONFD_OK;
}

static int cb_set_elem(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp,
                       confd_value_t *newval)
{
    char target_path[BUFSIZ];
    CHECK(translate_path(kp, target_path), "failed to translate path");
    CHECK(maapi_set_elem(maapisock, tctx->thandle, newval, "%s", target_path), "set_elem failed");
    return CONFD_OK;
}

static int cb_create(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp)
{
    char target_path[BUFSIZ];
    CHECK(translate_path(kp, target_path), "failed to translate path");
    CHECK(maapi_create(maapisock, tctx->thandle, "%s", target_path), "create failed");
    return CONFD_OK;
}

static int cb_remove(struct confd_trans_ctx *tctx, confd_hkeypath_t *kp)
{
    char target_path[BUFSIZ];
    CHECK(translate_path(kp, target_path), "failed to translate path");
    CHECK(maapi_delete(maapisock, tctx->thandle, "%s", target_path), "remove failed");
    return CONFD_OK;
}

int main(int argc, char **argv)
{
    int res = CONFD_OK;

    // initialize the library as a first mandatory step
    confd_init(DAMEON_NAME_STR, stderr, get_debug_level(argc, argv));

    // ConfD address to be contacted
    in_addr_t confd_addr = inet_addr("127.0.0.1");

    struct confd_daemon_ctx *dctx = confd_init_daemon(DAMEON_NAME_STR);
    if (NULL == dctx) {
        confd_fatal("Failed to initialize confd\n");
    }

    // load schemas to get a nicer prints (keypath tag names etc.)
    struct sockaddr_in confd_sock_addr =
        get_sockaddr_by_ip_port(confd_addr, CONFD_PORT);
    res = confd_load_schemas((struct sockaddr*)&confd_sock_addr,
                             sizeof (struct sockaddr_in));
    if (res != CONFD_OK) {
        confd_fatal("Failed to load schemas from confd\n");
    }
    TRACE("Schemas loaded.");

    ctlsock = confd_sock_init(confd_addr, CONFD_PORT, dctx, CONTROL_SOCKET);
    workersock = confd_sock_init(confd_addr, CONFD_PORT, dctx, WORKER_SOCKET);

    // register the transformation callpoint
    struct confd_trans_cbs tcb = {.init = init_transformation,
                                  .finish = finish_transformation};
    confd_register_trans_cb(dctx, &tcb);
    struct confd_data_cbs data = {.get_elem = cb_get_elem,
                                  .get_next = cb_get_next,
                                  .exists_optional = cb_exists_optional,
                                  .set_elem = cb_set_elem,
                                  .create   = cb_create,
                                  .remove   = cb_remove,
                                  .callpoint = symlinks__callpointid_servers_symlink};
    if (confd_register_data_cb(dctx, &data) == CONFD_ERR) {
        confd_fatal("Failed to register data cb \n");
    }
    if (confd_register_done(dctx) != CONFD_OK) {
        confd_fatal("Failed to complete registration \n");
    }
    maapisock = maapi_sock_init(confd_addr, CONFD_PORT);

    INFO("All registrations/init done, entering poll loop...");
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

    return 0;
}
