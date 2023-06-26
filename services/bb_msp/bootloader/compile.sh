#!/bin/sh

sudo gcc -I ./ main.c uart_if.c pinmux.c gpio_if.c utils.c bsl.c -o command_line_bsl
