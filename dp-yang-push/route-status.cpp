/*********************************************************************
 * Implements an operational data provider. The example randomly changes
 * operational data, which can be seen in yang-push NETCONF subscription.
 *
 * The demo is partly implemented in C++ to simplify implementation
 * (list, map, threading)
 *
 * See the README file for more information
 ********************************************************************/

using namespace std;

#include <iostream>
#include <string>
#include <memory>
#include <vector>
#include <algorithm>
#include <map>
#include <thread>

// use T_LOG_TRACE, T_LOG_DEBUG, T_LOG_INFO, T_LOG_WARN, T_LOG_ERROR to set log levels
// #define T_LOG_TRACE

extern "C" {
#include <sys/poll.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <confd_lib.h>
#include <confd_dp.h>
#define _TRACE_DECLARE
#include "traceh.h"
#include "route-status.h"
}

/********************************************************************/
/* Our daemon context and sockets as a global variable */
static struct confd_daemon_ctx *dctx;
static int ctlsock;
static int workersock;
static int num_routes;

/********************************************************************/
/* Helper functions */

void print_val(const char *str, const confd_value_t *val)
{
#ifdef T_LOG_TRACE
    if (val == NULL) {
        TRACE("%s == NULL", str);
    } else {
        const int buff_len = 256;
        char buffer[buff_len];
        confd_pp_value(buffer, buff_len, val);
        TRACE("%s == %s (type %i)", str, buffer, val->type);
    }
#endif
}

void print_path(const char *str, const confd_hkeypath_t *path)
{
    if (path == NULL)
        return;
#ifdef T_LOG_TRACE
    int buff_len = 256 - 1;
    char buffer[buff_len + 1];
    confd_pp_kpath(buffer, buff_len, path);
    buffer[buff_len] = '\0'; // ensure ending '\0' as confd doc does not say if is added
#endif
    TRACE("%s keypath == %s", str, buffer);
}

struct route_type {
    string id;
    int32_t leaf1;
    int32_t leaf2;
    int32_t leaf3;
    int32_t leaf4;
};

/*********************  C++ START *************************************/

static vector<unique_ptr<route_type>> routes; // use vector for get_next
static map<string, route_type*> routes_map; // use map for get_elem - more efficient search (uses more memory, but OK for test)

static void fill_routes(const int number)
{
    DEBUG_ENTER("number %i", number);
    for (int i = 1; i <= number; i++) {
        unique_ptr<route_type> rt(new route_type());
        rt->id = to_string(rand() % 100 + 1) + "rt" + to_string(i); // make random but unique key element
        rt->leaf1 = i * 2;
        rt->leaf2 = i * 3;
        rt->leaf3 = i * 4;
        rt->leaf4 = i * 5;
        TRACE("Adding to map %s", rt->id.c_str());
        routes_map[rt->id] = rt.get(); // duplicate pointer to map for efficient search
        TRACE("Adding to vector %s", rt->id.c_str());
        routes.push_back(std::move(rt));
    }
    TRACE("Sorting");
    // ConfD requires data are in sorted order unless tailf:sort=order unsorted is used
    std::sort(routes.begin(), routes.end(),
            [](unique_ptr<route_type> &a, unique_ptr<route_type> &b) {
                return b->id > a->id;
            });
    DEBUG_EXIT("routes.size()=%i", routes.size());
}

static void clear_routes()
{
    DEBUG_ENTER("");
    routes.clear();
    routes_map.clear();
    DEBUG_EXIT("");
}

static route_type* get_route(const string &id)
{
    DEBUG_ENTER("");
    auto rt = routes_map[id]; // version with MAP - more efficient search

//    vector<route_type*>::iterator it = find_if(routes.begin(), routes.end(), [&id](route_type*& r) {
//        return (r->id == id);
//    });
//    auto rt = *it;

    DEBUG_EXIT("");
    return rt;
}

/*********************  C++ END *************************************/

static int s_init(struct confd_trans_ctx *tctx)
{
    DEBUG_ENTER("");
    int ret = CONFD_OK;
    confd_trans_set_fd(tctx, workersock);
    DEBUG_EXIT("ret %i", ret);
    return ret;
}

static int s_finish(struct confd_trans_ctx *tctx)
{
    DEBUG_ENTER("");
    int ret = CONFD_OK;
    DEBUG_EXIT("ret %i", ret);
    return ret;
}

static int get_route_value(const route_type *route, confd_value_t *v,
        const uint32_t tag)
{
    TRACE_ENTER("tag %u", tag);
    int ret = CONFD_OK;

    switch (tag) {
    case rs_leaf1:
        CONFD_SET_INT32(v, route->leaf1);
        break;
    case rs_leaf2:
        CONFD_SET_INT32(v, route->leaf2);
        break;
    case rs_id:
        CONFD_SET_CBUF(v, route->id.c_str(), route->id.size());
        break;
    case rs_leaf3:
        CONFD_SET_INT32(v, route->leaf3);
        break;
    case rs_leaf4:
        CONFD_SET_INT32(v, route->leaf4);
        break;
    default:
        FATAL("get_elem - REQUST FOR UNKNOW LEAF tag %u", tag);
        break;
    }

    TRACE_EXIT("ret %i", ret);
    return ret;
}

/* Keypath example */
/* /routes-status(id}/leaf1 */

static int get_elem(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath)
{
    TRACE_ENTER("");
    print_path("", keypath);
    int ret = CONFD_OK;
    confd_value_t v;
    route_type *rt = NULL;

    // find route with given id
    const string id = CONFD_GET_CBUFPTR(&keypath->v[1][0]);
    rt = get_route(id);

    if (rt) {
        ret = get_route_value(rt, &v, CONFD_GET_XMLTAG(&(keypath->v[0][0])));
        confd_data_reply_value(tctx, &v);
    } else {
        confd_data_reply_not_found(tctx);
    }

    TRACE_EXIT("ret %i", ret);
    return ret;
}

static void fill_confd_values(const route_type *rt, confd_value_t *v)
{
    TRACE_ENTER("rt->id %s", rt->id.c_str());
    CONFD_SET_STR(&v[0], rt->id.c_str());
    CONFD_SET_INT32(&v[1], rt->leaf1);
    CONFD_SET_INT32(&v[2], rt->leaf2);
    CONFD_SET_INT32(&v[3], rt->leaf3);
    CONFD_SET_INT32(&v[4], rt->leaf4);
    TRACE_EXIT("");
}

static int get_next(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath,
        long next)
{
    TRACE_ENTER("next %i routes.size() %u", next, routes.size());
    print_path("", keypath);
    int ret = CONFD_OK;
    route_type *rt = NULL;

    if (next >= (long) routes.size() || routes.size() == 0) {
        TRACE("No more route entry");
        confd_data_reply_next_key(tctx, NULL, -1, -1);
        goto end;
    }

    if (next == -1) { /* first call */
        next = 0;
    }
    rt = routes[next].get();
    next++;

    if (rt) {
        confd_value_t v;
        TRACE("Setting route with id %s new next %i", rt->id.c_str(), next);
        CONFD_SET_STR(&v, rt->id.c_str());
        confd_data_reply_next_key(tctx, &v, 1, next);
    }

    end:
    TRACE_EXIT("ret %i", ret);
    return ret;
}

static int get_next_object(struct confd_trans_ctx *tctx,
        confd_hkeypath_t *keypath, long next)
{
    TRACE_ENTER("next=%i routes.size()=%u", next, routes.size());
    print_path("", keypath);
    int ret = CONFD_OK;
    route_type *rt = NULL;

    if (next >= (long) routes.size() || routes.size() == 0) {
        TRACE("No more route entry");
        confd_data_reply_next_key(tctx, NULL, -1, -1);
        goto end;
    }

    if (next == -1) { /* first call */
        next = 0;
    }
    rt = routes[next].get();
    next++;

    if (rt) {
        confd_value_t v[5];
        fill_confd_values(rt, v);
        ret = confd_data_reply_next_object_array(tctx, v, 5, next);
    }

    end:
    TRACE_EXIT("ret %i", ret);
    return ret;
}

static int get_object(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath)
{
    TRACE_ENTER("");
    print_path("", keypath);
    int ret = CONFD_OK;
    route_type *rt;

    const string id = CONFD_GET_CBUFPTR(&keypath->v[0][0]);
    rt = routes_map[id];

    if (rt) {
        confd_value_t v[5];
        fill_confd_values(rt, v);
        ret = confd_data_reply_value_array(tctx, v, 5);
    } else {
        confd_data_reply_not_found(tctx);
    }

    TRACE_EXIT("ret %i", ret);
    return ret;
}

// adapted from examples.confd/netconf_yang_push
static struct confd_push_on_change_ctx *push_ctx;

static int cb_subscribe_on_change(struct confd_push_on_change_ctx *pctx)
{
    INFO_ENTER("");
    int ret = CONFD_OK;

    if (push_ctx) {
        FATAL("multiple subscriptions are not supported.");
        ret = CONFD_ERR;
    } else {
        INFO("subscribe subid: %d, usid: %d, "
                "xpath_filter: %s, num_hkpaths: %d, dampening_period: %d, "
                "excluded_changes: %d\n", pctx->subid, pctx->usid,
                pctx->xpath_filter, pctx->npaths, pctx->dampening_period,
                pctx->excluded_changes);
        push_ctx = pctx;
    }

    TRACE_EXIT("ret %i", ret);
    return ret;
}

static int cb_unsubscribe_on_change(struct confd_push_on_change_ctx *pctx)
{
    INFO_ENTER("pctx->subid=%d", pctx->subid);
    int ret = CONFD_OK;

    push_ctx = NULL;

    TRACE_EXIT("ret %i", ret);
    return ret;

}

static void getdatetime(struct confd_datetime *datetime)
{
    TRACE_ENTER("");
    struct tm tm;
    struct timeval tv;

    gettimeofday(&tv, NULL);
    gmtime_r(&tv.tv_sec, &tm);

    memset(datetime, 0, sizeof(*datetime));
    datetime->year = 1900 + tm.tm_year;
    datetime->month = tm.tm_mon + 1;
    datetime->day = tm.tm_mday;
    datetime->sec = tm.tm_sec;
    datetime->micro = tv.tv_usec;
    datetime->timezone = 0;
    datetime->timezone_minutes = 0;
    datetime->hour = tm.tm_hour;
    datetime->min = tm.tm_min;
    TRACE_EXIT("");
}

static void cb_push_on_change(route_type *rt)
{
    INFO_ENTER("");
    if (push_ctx) {
        TRACE("push_ctx->subid=%d", push_ctx->subid);
        struct confd_datetime time;
        confd_tag_value_t tv1[1];
        getdatetime(&time);
        struct confd_data_edit edits[1];
        struct confd_data_edit *ed1 = (struct confd_data_edit*) malloc(
                sizeof(struct confd_data_edit));
        *ed1 = CONFD_DATA_EDIT();
        ed1->edit_id = (char*) "rt-edit-1";
        ed1->op = CONFD_DATA_REPLACE;
        CONFD_DATA_EDIT_SET_PATH(ed1, target,
                "/rs:route-status/route{%s}/leaf1", rt->id.c_str());
        int i = 0;
        CONFD_SET_TAG_INT32(&tv1[i++], rs_leaf1, rt->leaf1);
        ed1->data = tv1;
        ed1->ndata = i;
        edits[0] = *ed1;

        struct confd_data_patch *patch = (struct confd_data_patch*) malloc(
                sizeof(struct confd_data_patch));
        *patch = CONFD_DATA_PATCH(); /* Init patch with zeroes */
        patch->patch_id = (char*)"first-patch";
        patch->comment = (char*) "An example patch from data provider.";
        patch->edits = edits;
        patch->nedits = 1;

        patch->flags = CONFD_PATCH_FLAG_BUFFER_DAMPENED
                | CONFD_PATCH_FLAG_FILTER;
        confd_push_on_change(push_ctx, &time, patch);
        free(ed1);
        free(patch);

    }
    INFO_EXIT("");
}
/********************************************************************/

void init_confd()
{
    INFO_ENTER("");
    struct sockaddr_in addr;
    confd_debug_level debuglevel = CONFD_DEBUG;
#ifdef T_LOG_TRACE
    debuglevel = CONFD_TRACE;
#endif
    struct confd_trans_cbs trans;
    struct confd_data_cbs data;

    memset(&trans, 0, sizeof(struct confd_trans_cbs));
    trans.init = s_init;
    trans.finish = s_finish;

    memset(&data, 0, sizeof(struct confd_data_cbs));
    data.get_elem = get_elem;
    data.get_next = get_next;
    data.get_object = get_object;
    data.get_next_object = get_next_object;
    strcpy(data.callpoint, rs__callpointid_routestat);
    const char *daemon_name = "router_daemon";
    confd_init(daemon_name, stderr, debuglevel);

    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_family = AF_INET;
    addr.sin_port = htons(CONFD_PORT);

    if (confd_load_schemas((struct sockaddr*) &addr,
            sizeof(struct sockaddr_in)) != CONFD_OK)
        confd_fatal("Failed to load schemas from confd\n");

    if ((dctx = confd_init_daemon(daemon_name)) == NULL)
        confd_fatal("Failed to initialize confdlib\n");

    /* Create the first control socket, all requests to */
    /* create new transactions arrive here */

    if ((ctlsock = socket(PF_INET, SOCK_STREAM, 0)) < 0)
        confd_fatal("Failed to open ctlsocket\n");
    if (confd_connect(dctx, ctlsock, CONTROL_SOCKET, (struct sockaddr*) &addr,
            sizeof(struct sockaddr_in)) < 0)
        confd_fatal("Failed to confd_connect() to confd \n");

    /* Also establish a workersocket, this is the most simple */
    /* case where we have just one ctlsock and one workersock */

    if ((workersock = socket(PF_INET, SOCK_STREAM, 0)) < 0)
        confd_fatal("Failed to open workersocket\n");
    if (confd_connect(dctx, workersock, WORKER_SOCKET, (struct sockaddr*) &addr,
            sizeof(struct sockaddr_in)) < 0)
        confd_fatal("Failed to confd_connect() to confd \n");

    if (confd_register_trans_cb(dctx, &trans) == CONFD_ERR)
        confd_fatal("Failed to register trans cb \n");

    if (confd_register_data_cb(dctx, &data) == CONFD_ERR)
        confd_fatal("Failed to register data cb \n");

    struct confd_push_on_change_cbs pcb;
    memset(&pcb, 0, sizeof(pcb));
    pcb.fd = workersock;
    pcb.subscribe_on_change = cb_subscribe_on_change;
    pcb.unsubscribe_on_change = cb_unsubscribe_on_change;
    pcb.cb_opaque = NULL;
    strcpy(pcb.callpoint, rs__callpointid_routestat);
    if (confd_register_push_on_change(dctx, &pcb) == CONFD_ERR)
        confd_fatal("Failed to register push on change cb \n");

    if (confd_register_done(dctx) != CONFD_OK)
        confd_fatal("Failed to complete registration \n");
    INFO_EXIT("");
}

void generate_changes()
{
    INFO_ENTER("");
    TRACE("Num of routes=%i", routes.size());
    while (true) {
        int rt_idx = rand() % routes.size();
        TRACE("tr_idx=%i", rt_idx);
        route_type *rt = NULL;
        rt = routes[rt_idx].get();
        rt->leaf1 = rand() % 10 + 1;
        cb_push_on_change(rt);
        sleep(2);
    }
    INFO_EXIT("");
}

int confd_loop()
{
    INFO_ENTER("");
    int ret = CONFD_OK;

    while (1) {
        struct pollfd set[2];

        set[0].fd = ctlsock;
        set[0].events = POLLIN;
        set[0].revents = 0;

        set[1].fd = workersock;
        set[1].events = POLLIN;
        set[1].revents = 0;

        if (poll(set, sizeof(set) / sizeof(*set), -1) < 0) {
            perror("Poll failed:");
            break;
        }

        /* Check for I/O */
        if (set[0].revents & POLLIN) {
            if ((ret = confd_fd_ready(dctx, ctlsock)) == CONFD_EOF) {
                confd_fatal("Control socket closed\n");
            } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
                confd_fatal("Error on control socket request: %s (%d): %s\n",
                        confd_strerror(confd_errno), confd_errno,
                        confd_lasterr());
            }
        }
        if (set[1].revents & POLLIN) {
            if ((ret = confd_fd_ready(dctx, workersock)) == CONFD_EOF) {
                confd_fatal("Worker socket closed\n");
            } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
                confd_fatal("Error on worker socket request: %s (%d): %s\n",
                        confd_strerror(confd_errno), confd_errno,
                        confd_lasterr());
            }
        }
    }

    INFO_EXIT("ret %i", ret);
    return ret;
}

// pass one numeric parameter specifying nunmber of records (eg. ./route-status 1000)
int main(int argc, char *argv[])
{
    INFO_ENTER("argc %i", argc);
    int ret = CONFD_OK;
    bool arg_ok = true;

    if (argc != 2) {
        arg_ok = false;
    }

    if (arg_ok) {
        num_routes = stoi(argv[1]);
        init_confd();
        INFO("Number of routes to generate %i", num_routes);
        fill_routes(num_routes);
        std::thread change_thread(generate_changes);
        ret = confd_loop();
        clear_routes();
        change_thread.join();
    } else {
        ret = CONFD_ERR;
    }

    INFO_EXIT("ret %i", ret);
    return ret;
}

/********************************************************************/
