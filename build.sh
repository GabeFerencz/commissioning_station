#! /bin/bash

# Ensure any error will abort the script
set -e

# Get the git version string from the tag
GIT_TAG=$(git describe --long --tags --always --dirty)

echo Building $GIT_TAG...

rm -rf ./dist/*

python release_builder.py $GIT_TAG
pyinstaller CommissioningStation.py \
	--clean \
	--noconsole \
	--icon=images/CommissioningStation.ico \
	-p equipment \
	-p procedures
cp -r ./images ./dist/CommissioningStation/images
cp -r ./config ./dist/CommissioningStation/config

mv ./dist/CommissioningStation  ./dist/CommissioningStation_$GIT_TAG

rm release.py
rm -r ./build/
rm CommissioningStation.spec
rm -f *.pyc
rm -f equipment/*.pyc
rm -f procedures/*.pyc