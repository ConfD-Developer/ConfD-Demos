## What is this

This example shows a sample web application (running over a ConfD's webserver)
for managing device configuration defined by YANG modules. This is done by
utilizing the ConfD JSON-RPC API.

Please note that this is by NO means an official replacement of deprecated
WEB-UI of ConfD, or production ready product! It is an example on how you can
implement (parts of) new own solution, tailored and adjusted to your specific
web app needs and conditions.

For quick steps to run the example, see sections "Build" and "Running the demo" further below.

Following sections briefly describe architecture, and some
implementation details.

## ConfD webserver served contents

Example shows one of many possible ways on how to utilize ConfD JSON-RPC API,
to display and modify state and configuration of ConfD YANG models.
It dynamically generates a tree-like GUI structure representing the YANG model
and allows to perform most basic user operations - browsing, modifying, etc.

For details on ConfD web UI development and ConfD JSON-RPC,
please see ConfD user guide chapters:

- Web UI Development
- The JSON-RPC API

File `TODO` located as a sibling of this README contains a list of items
explicitly missing from current implementation. It is NOT a complete list of existing TODO/missing features!

## Dependencies

As web-dev world offers many variants and frameworks/libraries beyond scope
of this example - please note that selection of the ones used here is based
purely on personal preference and can be substituted as needed. Same is valid
for SPA vs multiple page architecture, and/or Vue.js SFC vs HTML & JavaScript
(TypeScript) code separation into standalone files.

Vue.js users - please note that the example came into existence before stable
release of Vue.js 3.x - Composition API, and has used the Vue 2.x options originally.

Lately this was refactored for latest versions of its dependencies/architecture.

- state management is now done using Pinia (removed Vuex)
- converted JavaScript files into TypeScript
- type-annotations were added where practical within example's scope/effort
- few api tests are run using Vitest (removed Jest)
  TODO - add brief description/warning?!

Following are noteworthy components used for implementation of this demo:

- Vue.js - The Progressive JavaScript Framework - https://vuejs.org/
  as a core JavaScript framework.

- Pinia - The intuitive store for Vue.js - https://pinia.vuejs.org/
  for state management of the web application.

- Quasar Framework - UI components library - https://quasar.dev/
  as the graphical UI components for Vue.js and the whole project template.

- AXIOS - Promise based HTTP client for the browser and node.js - https://github.com/axios/axios
  for communicating with target ConfD device. Used for exchanging JSON-RPC
  POST messages between this GUI "client" and ConfD "server".

- Vitest - Next Generation Testing Framework - https://vitest.dev/
  as an example of some "integration" tests between webui frontend and ConfD server to verify JSON-RPC compatibility.

## Webapp architecture

The whole webapp is designed as a Vue.js Single Page Application. It does not
provide multiple pages with content, but dynamically changes the single page
DOM when user actions are performed. It acts as a client connecting to a ConfD
webserver using JSON-RPC API. It allows the user to open read or write transaction
towards device and perform display/change of the configuration/state data.

Whenever user actions are taken, or the UI is displayed, the webapp ad-hoc dispatches
POST requests using the AXIOS library towards ConfD JSON-RPC port. Utilizing
reactive nature of Vue.JS app, UI is then updated using response data.

Main UI consists of 3 primary parts:

a) DEVICE CONFIG
Shows list of YANG modules managed by ConfD that include some configuration /
state data. It retrieves YANG model schema from ConfD, progressively one level
at a time, and automatically generates tree-like structure that allows user to
browse/modify the data.

b) YANG MODULES
Displays list of all the YANG modules managed/loaded by ConfD. It loads the
whole YANG schema in one JSON-RPC message, and shows the YANG types and data
structure in tree-like format.

c) JSON-RPC
Shows queue of all the JSON-RPC messages exchanged with ConfD "server". This
allows to look into raw request/response data, and can serve as an explanation
of the backend IPC when working in one of main application tabs ( a) / b) ).

Some noteworthy directories in the codebase:

webapp/src/boot - init of application's custom internals
webapp/src/components - all the UI components of the webapp
webapp/src/ts -
/confd-json-rpc - definition of used ConfD JSON-RPC messages
/tasks - async tasks using JSON-RPC used in UI components
/treenodes - config tree nodes specific codebase
webapp/src/router - app router built into quasar project, unused
webapp/src/store - app internal state implementation via Vuex store

## Build

Depending on your system, you may need to install some extra tools to
successfully build the web-application for ConfD to run.

Webapp project uses (requires) yarn - a JS package manager, and Quasar
CLI to build a "distribution" files for ConfD webserver to serve/use.

In general, internet connection is required at least for first build, for
Webapp build dependencies to be downloaded by project build framework.

You can check available tools via following commands:
(excluding "dev$" - a dummy bash command indicator)

```bash
dev$ yarn --version
1.22.22
```

If the tool is not installed on your platform, please see:

https://yarnpkg.com/getting-started/install

Quasar CLI installs automatically via yarn as one of the project dependencies.

To prepare project build, active internet connection is required to download all dependencies.

All dependencies will be downloaded into "webapp/node_modules" subdirectory.
Please note that approximately 365+MB of data dependencies may be downloaded
in the local directory. This is specific to our implementation architecture,
and can vary by changing its features.

## Running the demo

Regular Makefile commands can be used to run & build the example.
The build is split into two independent steps:

a) `dev$ make all`
to build and prepare all the ConfD related files.

b) `dev$ make docroot`
to build the web application and copy the webserver contents into ConfD's
webserver docroot directory.

When steps a), b) are completed (in any order), you can start ConfD via:

```bash
dev$ make start
```

At this point, all the configured northbound APIs should be ready.
Visit URL:

https://localhost:8888

in your preferred web browser to see the example webui.

Beware! There is no convenience layer/redirects in this example's web-server setup - If you attempt to connect http:///localhost:8888 (note missing "s") you may get "trash" output instead of a UI screen.

## Testing

Example includes only a very basic "integration" tests covering some parts of
TypeScript code utilizing JSON-RPC API.
Tests require a running ConfD server/instance, to run XHTML requests against.

You can execute tests including ConfD startup by using a Makefile target:

```bash
dev$ make testrun
```

If you've started ConfD instance manually or by other means, you can run the tests only:

```bash
dev$ make tests
```

## Developer playground

You may want to play with codebase and do various changes to the example.
It is possible to run webapp using integrated dev-server quite easily.

You can build and start only ConfD, via Makefile target:

```bash
dev$ make stop clean all start
```

You can now skip the "docroot" making step, and run:

```bash
dev$ make devrun
```

This starts development server, and webapp running on HTTP port 8080
(instead of HTTPS 8888 as in regular build).

You can install "Vue.js devtools" to your favorite browser for extra
debugging information etc.
