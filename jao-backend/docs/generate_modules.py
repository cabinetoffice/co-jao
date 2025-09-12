#!/bin/bash
# Generate module documentation
sphinx-apidoc -o source ../ -f --module-first --separate
