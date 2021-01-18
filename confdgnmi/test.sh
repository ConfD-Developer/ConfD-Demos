# this is helper command to run pytest tests from command line nad pass parameters
# e.g.
# ./test.sh -s -v tests
# ./test.sh -s -v -m unit tests
# ./test.sh -s -v -m api tests
# ./test.sh -s -v -m api -o log_cli=true tests
PYTHONPATH=./src:./tests:${PYTHONPATH} pytest "$@"