#/usr/bin env bash

rm -r htmlcov
python3 -m coverage run -m unittest process_faq.py 
python3 -m coverage html

