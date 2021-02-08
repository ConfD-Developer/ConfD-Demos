# this is helper command to run pytest tests from command line nad pass parameters
# e.g.
# ./test.sh -s -v tests
# ./test.sh -s -v -m unit tests
# ./test.sh -s -v -m api tests
# ./test.sh -s -v -m api -o log_cli=true tests
# ./test.sh -o log_cli=true -s -v tests/test_client_server.py::TestGrpc::test_subscribe_stream -k AdapterType.API
# ./test.sh -s -v --count=2 --repeat-scope session  tests #req. pytest-repeat plugin
PYTHONPATH=./src:./tests:${PYTHONPATH} pytest "$@"