#!/bin/bash
file_path=$(readlink -f "$0")
root_dir=$(dirname "$file_path")
cd "${root_dir}"

python3 -m unittest discover -s tests
