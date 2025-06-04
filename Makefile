# Makefile for Rerechan02 compiler

CC = gcc
CFLAGS = -Wall -Wextra -std=c11
RERE_COMPILER = src/compiler/rerec.py
BUILD_DIR = build

.PHONY: all clean test

all: dirs runtime compiler examples

dirs:
	mkdir -p $(BUILD_DIR)

runtime: dirs
	$(CC) $(CFLAGS) -c src/runtime/rere_runtime.c -o $(BUILD_DIR)/rere_runtime.o

compiler:
	chmod +x $(RERE_COMPILER)

examples/%: examples/%.rere runtime compiler
	$(RERE_COMPILER) $< -o $@
	chmod +x $@

examples: examples/hello

test: examples
	./examples/hello

clean:
	rm -rf $(BUILD_DIR) examples/hello examples/*.c
