#! /bin/bash
set -e

echo "$(date) - Running init.py"
python3 init.py

echo "$(date) - Waiting 10 seconds"
sleep 10

echo "$(date) - Running autograder.py"
python3 autograder.py

echo "$(date) - Running reset.py"
python3 reset.py