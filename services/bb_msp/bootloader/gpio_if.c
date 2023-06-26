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
#include <stdbool.h>
#include <stdlib.h>
#include "gpio_if.h"
#include "pinmux.h"

//int ResetPin = 50;
//int TestPin = 51;
int ResetPin = 44;
int TestPin = 45;

//****************************************************************************
//                      GLOBAL VARIABLES                                   
//****************************************************************************
char cmdString[100];

//****************************************************************************
//                      LOCAL FUNCTION DEFINITIONS                          
//****************************************************************************

//*****************************************************************************
//
//! GPIO Enable & Configuration
//!
//! \param  gpio
//!
//! \return None
//
//*****************************************************************************
void
GPIO_IF_setAsOutputPin(gpioEnum_t gpio)
{
	unsigned int creg;
    // Get direction control register contents
    switch((int)gpio/32)
    {
    	case 0:
    		creg = *(gpio0_port + GPIO_OE);
    		creg = creg & (~(1<<(gpio%32)));
    		*(gpio0_port + GPIO_OE) = creg;
    		break;
		case 1:
    		creg = *(gpio1_port + GPIO_OE);
    		creg = creg & (~(1<<(gpio%32)));
    		*(gpio1_port + GPIO_OE) = creg;
    		break;
		case 2:
    		creg = *(gpio2_port + GPIO_OE);
    		creg = creg & (~(1<<(gpio%32)));
    		*(gpio2_port + GPIO_OE) = creg;
    		break;
		case 3:
    		creg = *(gpio3_port + GPIO_OE);
    		creg = creg & (~(1<<(gpio%32)));
    		*(gpio3_port + GPIO_OE) = creg;
    		break;
		default:
			return;
    }
}

//*****************************************************************************
//
//! GPIO Enable & Configuration
//!
//! \param  gpio
//!
//! \return None
//
//*****************************************************************************
void
GPIO_IF_setAsInputPin(gpioEnum_t gpio)
{
	unsigned int creg;

    switch((int)gpio/32)
    {
    	case 0:
    		creg = *(gpio0_port + GPIO_OE);
			creg = creg | (1<<(gpio%32));
			*(gpio0_port + GPIO_OE) = creg;
    		break;
		case 1:
			creg = *(gpio1_port + GPIO_OE);
			creg = creg | (1<<(gpio%32));
			*(gpio1_port + GPIO_OE) = creg;
    		break;
		case 2:
			creg = *(gpio2_port + GPIO_OE);
			creg = creg | (1<<(gpio%32));
			*(gpio2_port + GPIO_OE) = creg;
    		break;
		case 3:
			creg = *(gpio3_port + GPIO_OE);
			creg = creg | (1<<(gpio%32));
			*(gpio3_port + GPIO_OE) = creg;
    		break;
		default:
			return;
    }
	
}

//*****************************************************************************
//
//! Turn gpio On
//!
//! \param  gpio
//!
//! \return none
//!
//! \brief  Turns a specific gpio On
//
//*****************************************************************************
void
GPIO_IF_setOutputHighOnPin(gpioEnum_t gpio)
{
	switch((int)gpio/32)
    {
    	case 0:
			*(gpio0_port + GPIO_OUT) = *(gpio0_port + GPIO_OUT) | (1<<(gpio%32));
    		break;
		case 1:
			*(gpio1_port + GPIO_OUT) = *(gpio1_port + GPIO_OUT) | (1<<(gpio%32));
    		break;
		case 2:
			*(gpio2_port + GPIO_OUT) = *(gpio2_port + GPIO_OUT) | (1<<(gpio%32));
    		break;
		case 3:
			*(gpio3_port + GPIO_OUT) = *(gpio3_port + GPIO_OUT) | (1<<(gpio%32));
    		break;
		default:
			return;
    } 
}

//*****************************************************************************
//
//! Turn gpio Off
//!
//! \param  gpio
//!
//! \return none
//!
//! \brief  Turns a specific gpio Off
//
//*****************************************************************************
void
GPIO_IF_setOutputLowOnPin(gpioEnum_t gpio)
{
	switch((int)gpio/32)
    {
    	case 0:
    		*(gpio0_port + GPIO_OUT) = *(gpio0_port + GPIO_OUT) & (~(1<<(gpio % 32)));
    		break;
		case 1:
			*(gpio1_port + GPIO_OUT) = *(gpio1_port + GPIO_OUT) & (~(1<<(gpio % 32)));
    		break;
		case 2:
			*(gpio2_port + GPIO_OUT) = *(gpio2_port + GPIO_OUT) & (~(1<<(gpio % 32)));
    		break;
		case 3:
			*(gpio3_port + GPIO_OUT) = *(gpio3_port + GPIO_OUT) & (~(1<<(gpio % 32)));
    		break;
		default:
			return;
    } 

}

//*****************************************************************************
//
//!  \brief This function returns gpio current Status
//!
//!  \param[in] gpio
//!
//!  \return 1: ON, 0: OFF
//
//*****************************************************************************
uint8_t
GPIO_IF_getPinStatus(gpioEnum_t gpio)
{
	uint8_t gpioStatus = 0;

	switch((int)gpio/32)
    {
    	case 0:
    		if ((*(gpio0_port + GPIO_IN) & (1<<(gpio % 32))) == (1<<(gpio % 32)))
		  	{
				gpioStatus = 1;
		  	}
    		break;
		case 1:
    		if ((*(gpio1_port + GPIO_IN) & (1<<(gpio % 32))) == (1<<(gpio % 32)))
		  	{
				gpioStatus = 1;
		  	}
    		break;
		case 2:
    		if ((*(gpio2_port + GPIO_IN) & (1<<(gpio % 32))) == (1<<(gpio % 32)))
		  	{
				gpioStatus = 1;
		  	}
    		break;
		case 3:
    		if ((*(gpio3_port + GPIO_IN) & (1<<(gpio % 32))) == (1<<(gpio % 32)))
		  	{
				gpioStatus = 1;
		  	}
    		break;
		default:
			return;
    } 

	return (gpioStatus);
}

//*****************************************************************************
//
//! Toggle the gpio state
//!
//! \param  gpio is the LED Number
//!
//! \return none
//!
//! \brief  Toggles a board gpio
//
//*****************************************************************************
void
GPIO_IF_toggleOutputOnPin(gpioEnum_t gpio)
{
	uint8_t gpioStatus = GPIO_IF_getPinStatus(gpio);

	if(gpioStatus == 1)
	{
		GPIO_IF_setOutputLowOnPin(gpio);
	}
	else
	{
		GPIO_IF_setOutputHighOnPin(gpio);
	}
}

//*****************************************************************************
//
// Close the Doxygen group.
//! @}
//
//*****************************************************************************
