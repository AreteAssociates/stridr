/*
 * Copyright (C) 2016 Texas Instruments Incorporated - http://www.ti.com/
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *    Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *    Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *    Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
*/

//******************************************************************************
// Version history:
// 1.0 07/17             Initial version. (Nima Eskandari)
// 1.1 07/17             Added Comments. (Nima Eskandari)
//----------------------------------------------------------------------------
//   Designed 2017 by Texas Instruments
//
//   Nima Eskandari
//   Texas Instruments Inc.
//   August 2017
//   Built with CCS Version: Code Composer Studio v7
//******************************************************************************

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <fcntl.h>
#include <sys/mman.h>
#include "pinmux.h"
#include "gpio_if.h"

//*****************************************************************************
//                      Defines
//*****************************************************************************
#define GPIO0_BASE 0x44E07000
#define GPIO1_BASE 0x4804C000
#define GPIO2_BASE 0x481AC000
#define GPIO3_BASE 0x481AE000

#define GPIO_SIZE  0x00000FFF

//*****************************************************************************
//                      GLOBAL VARIABLES
//*****************************************************************************
int mem_fd;

char *gpio0_map;
volatile unsigned *gpio0_port;

char *gpio1_map;
volatile unsigned *gpio1_port;

char *gpio2_map;
volatile unsigned *gpio2_port;

char *gpio3_map;
volatile unsigned *gpio3_port;

//*****************************************************************************
void
PinMuxConfig(void)
{
	FILE *pFile = NULL;

	// SBW Pins
	sprintf(cmdString,"%d", RESET_PIN);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",RESET_PIN);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

	sprintf(cmdString,"%d", TEST_PIN);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",TEST_PIN);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

	// LEDs
	sprintf(cmdString,"%d", LED1);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",LED1);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

	sprintf(cmdString,"%d", LED2);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",LED2);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

	sprintf(cmdString,"%d", LED3);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",LED3);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

	sprintf(cmdString,"%d", LED4);
	pFile = fopen("/sys/class/gpio/export", "w");
	fwrite(cmdString, 1, 2, pFile);
	fclose(pFile);

//	sprintf(cmdString,"/sys/class/gpio/gpio%d/direction",LED4);
//	pFile = fopen(cmdString, "w");
//	fwrite("out", 1, 3, pFile);
//	fclose(pFile);

//	printf("%s",cmdString);

	/* open /dev/mem */
    if ((mem_fd = open("/dev/mem", O_RDWR|O_SYNC) ) < 0) {
            printf("can't open /dev/mem \n");
            exit (-1);
    }

    /* mmap GPIO */

    /* GPIO0 */
    gpio0_map = (char *)mmap(
            0,
            GPIO_SIZE,
            PROT_READ|PROT_WRITE,
            MAP_SHARED,
            mem_fd,
            GPIO0_BASE
    );

    if (gpio0_map == MAP_FAILED) {
            printf("mmap error %d\n", (int)gpio0_map);
            exit (-1);
    }

    // Always use the volatile pointer!
    gpio0_port = (volatile unsigned *)gpio0_map;


	/* GPIO1 */
    gpio1_map = (char *)mmap(
            0,
            GPIO_SIZE,
            PROT_READ|PROT_WRITE,
            MAP_SHARED,
            mem_fd,
            GPIO1_BASE
    );

    if (gpio1_map == MAP_FAILED) {
            printf("mmap error %d\n", (int)gpio1_map);
            exit (-1);
    }

    // Always use the volatile pointer!
    gpio1_port = (volatile unsigned *)gpio1_map;

    /* GPIO2 */
    gpio2_map = (char *)mmap(
            0,
            GPIO_SIZE,
            PROT_READ|PROT_WRITE,
            MAP_SHARED,
            mem_fd,
            GPIO2_BASE
    );

    if (gpio2_map == MAP_FAILED) {
            printf("mmap error %d\n", (int)gpio2_map);
            exit (-1);
    }

    // Always use the volatile pointer!
    gpio2_port = (volatile unsigned *)gpio2_map;

    /* GPIO3 */
    gpio3_map = (char *)mmap(
            0,
            GPIO_SIZE,
            PROT_READ|PROT_WRITE,
            MAP_SHARED,
            mem_fd,
            GPIO3_BASE
    );

    if (gpio3_map == MAP_FAILED) {
            printf("mmap error %d\n", (int)gpio3_map);
            exit (-1);
    }

    // Always use the volatile pointer!
    gpio3_port = (volatile unsigned *)gpio3_map;
}
