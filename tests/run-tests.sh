#!/bin/bash
file_path=$(readlink -f "$0")
root_dir=$(dirname $(dirname "$file_path"))
cd "${root_dir}"

python3 -m unittest discover -v -s tests/unit
#python3 -m unittest discover -v -s tests/integration
