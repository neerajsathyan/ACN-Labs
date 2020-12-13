for package in ${GRPC_DEP_PACKAGES}; do
	pushd .
	cd third_party/${package}
	mkdir build
	cd build
	cmake -DBUILD_SHARED_LIBS=ON ../
	sudo make install -j${NUM_CORES}
	popd
done