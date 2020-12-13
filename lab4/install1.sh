# Copyright 2020 Lin Wang

# This code is part of the Advanced Computer Networks (2020) course at Vrije 
# Universiteit Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Navigate to the home directory
cd ~

# Source
BMV2_COMMIT="9982947acb075a18697a77e21e27e805e4167c05"  # October 25, 2020
PI_COMMIT="e16d99a18d3ad22d6f68b283e45d1441bc9b1bbd"    # October 25, 2020
P4C_COMMIT="159d29677df1eb39527864e38725e74d68c18714"   # October 25, 2020
PROTOBUF_COMMIT="v3.13.0"	# October 25, 2020
GRPC_COMMIT="v1.33.1"			# October 25, 2020

# Get the number of cores to speed up the compilation process
NUM_CORES=`grep -c ^processor /proc/cpuinfo`

# Protobuf 
git clone https://github.com/google/protobuf.git
cd protobuf
git checkout ${PROTOBUF_COMMIT}
export CFLAGS="-Os"
export CXXFLAGS="-Os"
export LDFLAGS="-Wl,-s"
./autogen.sh
./configure --prefix=/usr
make -j${NUM_CORES}
sudo make install
sudo ldconfig
unset CFLAGS CXXFLAGS LDFLAGS
# Force install python module
cd python
python setup.py build
sudo pip install .
cd ../..