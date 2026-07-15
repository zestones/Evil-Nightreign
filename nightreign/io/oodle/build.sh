#!/bin/sh
# Rebuild libooz.so (Oodle Kraken decompressor) from powzix/ooz sources.
# Only the Kraken path is needed for FromSoft DCX; LZNA/BitKnit are stubbed.
set -e
cd "$(dirname "$0")"
head -n 4286 kraken.cpp > kraken_lib.cpp   # drop the Windows CLI main()
g++ -O2 -fPIC -shared -msse4.1 -w kraken_lib.cpp oozwrap.cpp oozstep.cpp stubs.cpp -o libooz.so
echo "built libooz.so"
