#!/bin/sh

if [ -z "$1" ]; then
	echo "Please input the project name"
else
	proj="$1"
	printf 'Analysing genealogies for %s ...\n' $proj
	python analyse_genealogies.py $proj nicad
	python analyse_genealogies.py $proj iclones
	printf 'Extracting metrics for %s ...\n' $proj
	python independant_variables.py $proj nicad
	python independant_variables.py $proj iclones
fi