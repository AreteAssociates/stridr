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


#ifndef __GPIOIF_H__
#define __GPIOIF_H__

//*****************************************************************************
//
// If building with a C++ compiler, make all of the definitions in this header
// have a C binding.
//
//*****************************************************************************
#ifdef __cplusplus
extern "C"
{
#endif

extern int ResetPin;
extern int TestPin;

// BeagleBone User LEDs
typedef enum
{
    LED1 = 53,  /* gpio53 User 0 - GPIO1_21 */
    LED2 = 54,  /* gpio54 User 1 - GPIO1_22 */
    LED3 = 55,  /* gpio55 User 2 - GPIO1_23 */
    LED4 = 56,  /* gpio56 User 3 - GPIO1_24 */
    
} gpioEnum_t;


#define RESET_PIN	(gpioEnum_t)ResetPin
#define TEST_PIN	(gpioEnum_t)TestPin

// OE: 0 is output, 1 is input
#define GPIO_OE  0x14d
#define GPIO_IN  0x14e
#define GPIO_OUT 0x14f

extern char cmdString[100];

//*****************************************************************************
//
// API Function prototypes
//
//*****************************************************************************
extern void GPIO_IF_setAsOutputPin(gpioEnum_t gpio);
extern void GPIO_IF_setAsInputPin(gpioEnum_t gpio);
extern void GPIO_IF_setOutputHighOnPin(gpioEnum_t gpio);
extern void GPIO_IF_setOutputLowOnPin(gpioEnum_t gpio);
extern uint8_t GPIO_IF_getPinStatus(gpioEnum_t gpio);
extern void GPIO_IF_toggleOutputOnPin(gpioEnum_t gpio);

//*****************************************************************************
//
// Mark the end of the C bindings section for C++ compilers.
//
//*****************************************************************************
#ifdef __cplusplus
}
#endif

#endif //  __GPIOIF_H__

