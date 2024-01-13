#/usr/bin env bash

rm -rf htmlcov
python3 -m coverage run -a process_faq.py 
python3 -m coverage run -a test_treediff.py
python3 -m coverage run -a validator_test.py
python3 -m coverage html

