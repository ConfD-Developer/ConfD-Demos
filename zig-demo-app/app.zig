// *********************************************************************
// * ConfD action example written in Zig
// *
// * (C) 2021 Tail-f Systems
// * Permission to use this code as a starting point hereby granted
// * This is ConfD Sample Code.
// *
// * See the README file for more information
// ********************************************************************/

const std = @import("std");
const c_imp = @cImport({
    @cInclude("string.h");
    @cInclude("poll.h");
    @cInclude("confd_lib.h");
    @cInclude("confd_dp.h");
    @cInclude("confd.h");
});
const dm = @cImport(@cInclude("datamodel.h"));

// Set the log level to info
pub const log_level: std.log.Level = .info;

//pub const NULL = @import("std").zig.c_translation.cast(?*anyopaque, @as(c_int, 0));
pub const CONFD_ADDR: [*c]const u8 = "127.0.0.1";
pub const EXAMPLE_APP_NAME: [*c]const u8 = "app_example";
pub var ctlsock: c_int = undefined;
pub var workersock: c_int = undefined;
pub var dctx: [*c]c_imp.struct_confd_daemon_ctx = undefined;

pub fn initAction(arg_uinfo: [*c]c_imp.struct_confd_user_info) callconv(.C) c_int {
    std.log.info("==> initAction", .{});
    var rv: c_int = c_imp.CONFD_OK;
    var uinfo = arg_uinfo;

    c_imp.confd_action_set_fd(uinfo, workersock);
    std.log.info("<== initAction rv={}", .{rv});
    return rv;
}

pub fn traceConfdKp(txt: []const u8, kp: [*c]c_imp.confd_hkeypath_t) void {
    if (kp != null) {
        var buf: [1024]u8 = undefined;
        _ = c_imp.confd_pp_kpath(@ptrCast([*c]u8, &buf), buf.len, kp);
        std.log.info("{s}{s}", .{ txt, buf });
    } else {
        std.log.info("{s}{p}", .{ txt, &kp });
    }
}

pub export fn doAction(
    uinfo: [*c]c_imp.struct_confd_user_info,
    tag: [*c]c_imp.struct_xml_tag,
    kp: [*c]c_imp.confd_hkeypath_t,
    params: [*c]c_imp.confd_tag_value_t,
    n: c_int,
) c_int {
    var rv: c_int = c_imp.CONFD_OK;
    std.log.info("==> doAction uinfo.usid={} tag={} n={}", .{ uinfo.*.usid, tag.*.tag, n });
    traceConfdKp("kp=", kp);

    var i: u32 = 0; // no iterating for loop in Zig?
    while (i < n) : (i += 1) {
        var buf: [512]u8 = undefined;
        _ = c_imp.confd_pp_value(@ptrCast([*c]u8, &buf), buf.len, &params[i].v);
        std.log.info("param{}.tag={} param{}.v={s}", .{ i, &params[i].tag, i, buf });
    }

    std.log.info("<== doAction rv={}", .{rv});
    return rv;
}

const ConfDError = error{
    Err,
    LoadSchemas,
    Connect,
    Register,
    SocketDisconnected,
    SocketError,
    // TODO add other errors?
};

pub fn initConfdDaemon() !void {
    std.log.info("==>", .{});

    var debuglevel: c_uint = c_imp.CONFD_TRACE;
    std.log.info("debuglevel={}", .{debuglevel});
    c_imp.confd_init(EXAMPLE_APP_NAME, c_imp.stderr, debuglevel);

    var addr_in: c_imp.struct_sockaddr_in = undefined;
    addr_in.sin_addr.s_addr = c_imp.inet_addr(CONFD_ADDR);
    addr_in.sin_family = 2;
    addr_in.sin_port = c_imp.__bswap_16(4565); // needs to swap bits
    var addr = @ptrCast([*c]c_imp.struct_sockaddr, &addr_in);

    if (c_imp.CONFD_OK != c_imp.confd_load_schemas(addr, @sizeOf(c_imp.struct_sockaddr_in)))
        return ConfDError.LoadSchemas;
    dctx = c_imp.confd_init_daemon(EXAMPLE_APP_NAME);
    std.log.info("dctx.name={s}", .{dctx.*.name});

    ctlsock = c_imp.socket(c_imp.PF_INET, c_imp.SOCK_STREAM, 0);
    if (c_imp.CONFD_OK !=
        c_imp.confd_connect(dctx, ctlsock, c_imp.CONTROL_SOCKET, addr, @sizeOf(c_imp.struct_sockaddr_in)))
        return ConfDError.Connect;
    workersock = c_imp.socket(c_imp.PF_INET, c_imp.SOCK_STREAM, 0);
    if (c_imp.CONFD_OK !=
        c_imp.confd_connect(dctx, workersock, c_imp.WORKER_SOCKET, addr, @sizeOf(c_imp.struct_sockaddr_in)))
        return ConfDError.Connect;

    var acb: c_imp.struct_confd_action_cbs =
        @import("std").mem.zeroes(c_imp.struct_confd_action_cbs);
    acb.init = initAction;
    _ = c_imp.strncpy(&acb.actionpoint, dm.datamodel__actionpointid_search_point, 256);
    acb.action = doAction;
    if (c_imp.CONFD_OK != c_imp.confd_register_action_cbs(dctx, &acb))
        return ConfDError.Register;
    if (c_imp.CONFD_OK != c_imp.confd_register_done(dctx))
        return ConfDError.Register;

    std.log.info("<==", .{});
}

pub fn confdLoop() !void {
    std.log.info("==>", .{});

    while (true) {
        var set: [2]c_imp.struct_pollfd = undefined;
        set[0].fd = ctlsock;
        set[0].events = 1;
        set[0].revents = 0;
        set[1].fd = workersock;
        set[1].events = 1;
        set[1].revents = 0;
        if (c_imp.poll(&set, set.len, -1) < 0) {
            std.log.err("Poll failed:", .{});
            continue;
        }
        if ((set[0].revents & c_imp.POLLIN) != 0) {
            const ret = c_imp.confd_fd_ready(dctx, ctlsock);
            if (ret == -2) {
                std.log.err("Control socket closed!", .{});
                return ConfDError.SocketDisconnected;
            } else if ((ret == -1) and (c_imp.confd_errno_location().* != 19)) {
                const confd_errno = c_imp.confd_errno_location().*;
                const confd_strerror = c_imp.confd_strerror(c_imp.confd_errno_location().*);
                std.log.err("Error on control socket request: {s} {}: {s}", .{ confd_strerror, confd_errno, c_imp.confd_lasterr() });
                return ConfDError.SocketError;
            }
        }
        if ((set[1].revents & c_imp.POLLIN) != 0) {
            const ret = c_imp.confd_fd_ready(dctx, workersock);
            if (ret == -2) {
                std.log.err("Worker socket closed!", .{});
                return ConfDError.SocketDisconnected;
            } else if ((ret == -1) and (c_imp.confd_errno_location().* != 19)) {
                const confd_errno = c_imp.confd_errno_location().*;
                const confd_strerror = c_imp.confd_strerror(c_imp.confd_errno_location().*);
                std.log.err("Error on worker socket request: {s} {}: {s}", .{ confd_strerror, confd_errno, c_imp.confd_lasterr() });
                return ConfDError.SocketError;
            }
        }
    }

    std.log.info("<==", .{});
}

pub fn main() !void {
    std.log.info("==>", .{});

    try (initConfdDaemon());
    try (confdLoop());

    std.log.info("<==", .{});
}
