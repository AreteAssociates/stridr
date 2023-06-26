OPENCV_LIB = `pkg-config --libs opencv`
OPENCV_INC = `pkg-config --cflags opencv`

.PHONY: all
all: capture capture_hdr

capture: capture.cpp
	g++ ${OPENCV_INC} $< ${OPENCV_LIB} -o $@

capture_hdr: capture_hdr.cpp
	g++ ${OPENCV_INC} $< ${OPENCV_LIB} -o $@

.PHONY: clean
clean:
	-rm -f capture capture_hdr
