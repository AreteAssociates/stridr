/** \file rb_file.c
\brief Example: fetch ADC samples in a ring buffer and save to file.

This file contains an example on how to use the ring buffer mode of
libpruio.

second edit 3/19/19 - for BBlue -
Modified to take AIN-0 only.
        - only need 10 kHz sample rate
        - try to make it sample for e.g. 10 seconds
        - determine how to play back recorded audio
        - what encoding can be done, at present it is just 'raw' data,
                but that specification is unclear

// - no longer three steps --- A fixed step mask of AIN-0, AIN-1 and AIN-2 get configured
for maximum speed, sampled in to the ring buffer and from there saved
as raw data to some files. Find a functional description in section
\ref sSecExaRbFile.

Licence: GPLv3, Copyright 2014-\Year by \Mail

Thanks for C code translation: Nils Kohrs <nils.kohrs@gmail.com>

// Compile by: `gcc -Wall -o rb_file_ain6 rb_file_ain6.c -lpruio`
Compile by: `gcc -Wall -o ain0 ain0.c -lpruio`

\since 0.4.0
*/

#include "unistd.h"
#include "time.h"
#include "stdio.h"
#include "libpruio/pruio.h"
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define DEFAULT_SAMPLE_RATE 10000 // Hz

int main(int argc, char **argv)
{
    // vars for command line arguments
    char output_directory[100];
    int sample_rate;
    int sample_period;

    if ( (argc < 4) ||
         (strcmp(argv[1], "-h") == 0) ||
         (strcmp(argv[1], "--help") == 0) ||
         (strcmp(argv[1], "-help") == 0) )
    {
        // not enough arguments, give help
        printf("Error: not enough arguments!\n\n");
        printf("Audio logger.\n");
        printf("Usage instructions:\n ./audio_logger acquire_length opath rate\n");
        printf("Where:\n  acquire_length = the length of time to acquire data.\n  opath = the output file path\n  rate = (optional) the sampling frequency in Hz (default=10000 Hz)\n");
        printf("Example:\n ./audio_logger 30 /data/hydrophone 10000\n\n");
        return 0;
    }

    // handle command line arguments
    sample_period = atoi(argv[1]);
    strcpy(output_directory, argv[2]);
    strcat(output_directory, "/");

    // rate is optional
    if (argc < 4) sample_rate = DEFAULT_SAMPLE_RATE;
        else sample_rate=atoi(argv[3]);

    // create output directory if not exist
    if (-1 == access(output_directory, W_OK))
    {
        fprintf(stderr, "Output directory (%s) missing or not writeable.\r\n", output_directory);
        return -1;
    }

    //const uint32 tSamp = 300000;  // The number of samples in the files (per step). 30 sec at 10kHz =~ 586 kB
    //const uint32 tmr = 100000;    // The sampling rate in ns (100000 -> 10 kHz).
    const uint32 tSamp = sample_rate * sample_period;  // The number of samples in the files (per step). 30 sec at 10kHz =~ 586 kB
    const uint32 tmr = sample_rate * 10;    // The sampling rate in ns (100000 -> 10 kHz).
    const uint32 NoStep = 1;      // The number of active steps (must match setStep calls and mask).
    const uint32 NoFile = 1;      // The number of files to write. - changed to 1, also mod output file name
    const char *NamFil = strcat(output_directory, "AUDIO_%4u%02u%02uT%02u%02u%02u.000.log"); // The output file names
    struct timespec mSec;
    mSec.tv_nsec = 1000000;

    time_t t = time(NULL);
    struct tm tm = *gmtime(&t);

    pruIo *io = pruio_new(PRUIO_DEF_ACTIVE, 0, 0, 0); //! create new driver
    if (io->Errr){ printf("constructor failed (%s)\n", io->Errr); return 1; }

    do {        // execute once
                //      Parameters for pruio_adc_setStep:
                //      1: driver
                //      2: step# - for sample sequencing (of 16 possible)
                //      3: input channel (AIN-6 n this case)
                //      4: averaging (default 0),
                //      5: sample delay (def. 0),
                //      6: open delay (def. 0x98?)
                //
        // step 1, AIN-0
        if (pruio_adc_setStep(io, 1, 0, 0, 0, 0)){ printf("step 1 configuration failed: (%s)\n", io->Errr); break; }

        // bitmask for adc control register
        // there is only one step (for AIN-0)
        uint32 mask = 1 << 1;                                           // The active steps (1).
        uint32 tInd = tSamp * NoStep;                                   // The maximum total index.

        // below is halfway point of ring buffer?
        uint32 half = ((io->ESize >> 2) / NoStep) * NoStep;             // The maximum index of the half ring buffer.

        if (half > tInd){ half = tInd;}                                 //       adapt size for small files
        uint32 samp = (half << 1) / NoStep;                             // The number of samples (per step).

        if (pruio_config(io, samp, mask, tmr, 0)){ printf("config failed (%s)\n", io->Errr); break; } // configure driver
        if (pruio_rb_start(io)){ printf("rb_start failed (%s)\n", io->Errr); break; }

        uint16 *p0 = io->Adc->Value;                                    // A pointer to the start of the ring buffer.
        uint16 *p1 = p0 + half;                                         // A pointer to the middle of the ring buffer.
        uint32 n;                                                       // File counter.
        char fName[20];                                                 // file name

        // this will only iterate once - per number of files
        for(n = 0; n < NoFile; n++)
        {
            sprintf(fName, NamFil, tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec); // create file name: hydro_year-month-dayThourminutesecond.log
            printf("Creating file %s\n", fName);
            FILE *oFile = fopen(fName, "wb");
            uint32 i = 0;                                                       // Start index.
            while(i < tInd)                                                     // while < total index
            {
                i += half;                                                      // make index halfway point
                if(i > tInd)                                                    // fetch the rest(maybe no complete chunk)
                {
                    uint32 rest = tInd + half - i;                              // rest = total index + halfway - i (which is > total index)
                    uint32 iEnd = p1 >= p0 ? rest : rest + half;                        // if p1 >= p0, iEnd = rest, else iEnd = (rest + half)
                    while(io->DRam[0] < iEnd) nanosleep(&mSec, NULL);
                    printf("  writing samples %u-%u\n", tInd -rest, tInd-1);
                    fwrite(p0, sizeof(uint16), rest, oFile);                    // from index p0 in buffer, write to file
                    uint16 *swap = p0;
                    p0 = p1;
                    p1 = swap;
                    break;
                }
                if(p1 > p0) while(io->DRam[0] < half) nanosleep(&mSec, NULL);   // fill buffer < half
                else        while(io->DRam[0] > half) nanosleep(&mSec, NULL);   // fill buffer > half
                printf("  writing samples %u-%u\n", i-half, i-1);
                fwrite(p0, sizeof(uint16), half, oFile);                        // from p0 in buffer, write half to file
                uint16 *swap = p0;
                p0 = p1;
                p1 = swap;
            }
            fclose(oFile);
            printf("Finished file %s\n", fName);
        }
    } while(0);
    pruio_destroy(io);
    return 0;
}


