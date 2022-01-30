#!/bin/bash

echo "Running Unit tests"

pytest --random-order --cov=panther --cov-config=.coveragerc tests/
