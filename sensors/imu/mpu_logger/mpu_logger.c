/* 
`mpu_logger` is responsible for logging data from the IMU, processing basic sensor statistics
and calculating wave statistics

It is modifed from the robot contro library "rc_altitude.c"

Author information
------------------
SPA - Steve Anderson, spanderson@arete.com
JF - Jim Frield, jfriel@arete.com
PJR - P.J. Rusello, prusello@arete.com

Release Notes
=============
10/25/2019 PJR
    - General code cleanup to remove unused lines and confusing comments
    - Moved accelerometer low pass filter initialization out of the DMP callback
    - Added calculation of mean, variance, and co-variance <a_i * g_i> in logging code
    - Switched main sample loop to a for structure
    - Main sample loop now used to accumulate sums, sum of squares for statistics
    - Turned on gyro auto-calibration which seems to help prevent low frequency drift in roll, pitch, and yaw
    - Changed output file formats (see readme.txt)
    - Removed the acceleration vector rotation because of inconsistent behavior, code is available, just uncomment
        #define ROTATE_ACCEL on line 91

5/21/2019 SPA
    The height estimation from the real-time Kalmin filter is not working well
    Removed Kalmin filter completely
    So instead I created a process that runs after the collection on the vertical accelerations
    This is much more robust.
    NOTE: THIS WORKS WITH 1024 SAMPLE AT 4 HZ, BUT MIGHT BREAK IF YOU USE SOMETHING DIFFERENT
    $  ./mpu_logger 256 /home/debian/testdata 4

5/3/2019 SPA
    Jim added command line inputs for number of samples, the output directory and sample rate
    Rotated results for STRDR which has the MPU oriented Y-UP
    Still a lot of low wave_frequencies variance in the height data.  Needs more work for sure but
    might be good enough for Phase I

3/18/2019 SPA
    Adding in the wave spectral processing
    This also changes what is in the log file output
    Uses the FFTW3 library
    Makefile now must include:
        LDFLAGS		:= -pthread -lm -lrt -l:librobotcontrol.so.1 -L$HOME/usr/lib -lfftw3\
    New Output file for the wave spectrum

1/23/2019 SPA
    Reduce MPU output rate to 6 hz
    Change the date formats to ISO format in UTC
    Reduce number of save pts to 1024, this will run for about 170 seconds (<3minutes)
    Changed to usleep logic to make sure we are at fixed sample rate
    Changed so it will only run once, not continously
    Outputs log file that appends each time it is run

12/14/2018 SPA
    updated to
        save 3000 pts (no 3001)
        save BPR not derived barometric pressure height
        ave horizontal accelerations from fused_quat
 */
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <math.h> // for M_PI
#include <rc/math/filter.h>
#include <rc/math/quaternion.h>
#include <rc/time.h>
#include <rc/mpu.h>
#include <fftw3.h>
#include <unistd.h>
#include <string.h>
#include <time.h>

// function declarations since waveproc doesn't have a header
int waveproc(double* in, int NPTS, int HZ,double* significant_wave_height, double* dominant_period, double* power_spectrum,double* F);
int az2hgt(double* az, int NPTS, int HZ,double* wave_height);

// useful definitions
#define GRAVITY                     9.80665
#define DEFAULT_SAMPLE_TIME         180
#define DEFAULT_OUTPUT_DIR          "/data/imu/"
#define DEFAULT_OUTPUT_RATE         6
#define DEFAULT_N_SAMPLES           1024

// sensor orientation, filter setup, and internal sampling parameters
#define VERTICAL_AXIS               0 // IMU accelerometer x-axis is vertical, use 0
#define INTERNAL_SAMPLE_RATE        200 // hz
#define DT                          (1.0 / INTERNAL_SAMPLE_RATE)
#define ACCEL_LP_TC                 20*DT   // fast LP filter for accel from original version
// These defines control whether to calculate statistics during logging (other than mean wave height), rotate accelerations using the MPU, and logging of high rate low pass filtered data
#define CALCULATE_STATISTICS
//#define ROTATE_ACCEL
//#define OUTPUT_DMP

// global variables for the DMP callback
static rc_mpu_data_t mpu_data;
static rc_filter_t acc_lp = RC_FILTER_INITIALIZER;

#ifdef OUTPUT_DMP
    FILE* dmp_fid;
#endif

static void __dmp_handler(void)
{
    int i;
    double accel_vec[3];
    double az_from_lp;

    // make copy of acceleration reading before rotating
    for(i=0; i<3; i++) accel_vec[i]=mpu_data.accel[i];
    #ifdef ROTATE_ACCEL
        rc_quaternion_rotate_vector_array(accel_vec,mpu_data.dmp_quat);
        // need to pull from axis 2 (az, third acceleration) because the rotation
        // tries to put ax, ay horizontal and az vertical
        az_from_lp = rc_filter_march( &acc_lp, accel_vec[ 2 ] );
    #else
        az_from_lp = rc_filter_march( &acc_lp, accel_vec[ VERTICAL_AXIS ] );
    #endif

    // Used for diagnostic writes of high sample rate data
    #ifdef OUTPUT_DMP
        // time variables
        time_t t = time(NULL);
        uint64_t  nano_epoch;
        uint64_t sec_floor;
        uint64_t sec_hundredths;

        t = time(NULL);
        struct tm tm = *gmtime( &t );
        nano_epoch = rc_nanos_since_epoch();
        sec_floor = floor( ( nano_epoch / pow( 10, 9 ) ) );
        sec_hundredths = ( nano_epoch / pow( 10, 7 ) ) - sec_floor * 100;
        fprintf( dmp_fid, "%04d-%02d-%02dT%02d%02d%02d.%02d, ", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, (int) sec_hundredths );
        fprintf( dmp_fid, "%9.4f, %9.4f, %9.4f, %9.4f\n", mpu_data.accel[ 0 ], mpu_data.accel[ 1 ], mpu_data.accel[ 2 ], az_from_lp );
    #endif
    return;
}

int main( int argc, char *argv[] )
{
    // sampling setup
    int number_of_samples = DEFAULT_N_SAMPLES;
    int run_seconds = DEFAULT_SAMPLE_TIME;
    int rate = DEFAULT_OUTPUT_RATE; //report rate in Hz
    static int running = 0;
    rc_mpu_config_t mpu_conf;

    // IO variables
    FILE* fid;
    FILE* fid2;
    char output_directory[100];
    char fname [100];
    long cnt=0;
    int i;

    #ifdef OUTPUT_DMP
        char orientation_filename[] = "./imu_data/lowpass_dmp_data.text";
    #endif

    // copy the default output directory here, replacing it below if needed
    strcpy(output_directory, DEFAULT_OUTPUT_DIR );
    if ( argc == 2 )
    {
        if ( ( strcmp( argv[ 1 ], "-h") == 1 ) || 
             ( strcmp( argv[ 1 ], "--help") == 1 ) || 
             ( strcmp( argv[ 1 ], "-help") == 1 ) )
        {
            // give help
            printf("Error: Not enough arguments!\n\n");
            printf("IMU logger.\n");
            printf("Usage instructions:\n ./mpu_logger acquire_length opath rate\n");
            printf("Where:\n  acquire_length = the length of time to acquire data.\n  opath = the output file path\n  rate = (optional) the report rate in Hz (default=4 Hz).\n");
            printf("Data are acquired at %d Hz, but recorded at specified rate.\n\n", INTERNAL_SAMPLE_RATE);
            printf("Example:\n ./mpu_logger 128 /home/debian/testdata 4\n\n");
            return 0;
        }
        else
        {
            run_seconds = atoi( argv[ 1 ] );
        }
    }
    else if ( argc == 3 )
    {
        run_seconds = atoi( argv[ 1 ] );
        strcpy( output_directory, argv[ 2 ] );
    }
    else if ( argc == 4 )
    {
        run_seconds = atoi( argv[ 1 ] );
        strcpy( output_directory, argv[ 2 ] );
        rate = atoi( argv[ 3 ] );
    }
    
    strcat(output_directory, "/");
    number_of_samples = (int)(run_seconds * rate);

    // create output directory if not exist
    if (-1 == access(output_directory, W_OK)) {
        fprintf(stderr, "Output directory (%s) missing or not writeable.\r\n", output_directory);
        return -1;
    }

    #ifdef CALCULATE_STATISTICS
        // variables for holding samples and running statistics
        // using running totals to calculate mean and variance in one loop
        // for the fundamental sensor values of acceleration, gyroscope, and magnetometer
        double acceleration_sum[ 3 ] = { 0, 0, 0 };
        double ai_shift[ 3 ] = { 0, 0, 0 };
        double acceleration_shifted_sum[ 3 ] = { 0, 0, 0 };
        double acceleration_sos[ 3 ] = { 0, 0, 0 };
        double gyro_sum[ 3 ]  = { 0, 0, 0 };
        double gi_shift[ 3 ] = { 0, 0, 0 };
        double gyro_shifted_sum[ 3 ]  = { 0, 0, 0 };
        double gyro_sos[ 3 ] = { 0, 0, 0 };
        double magnetometer_sum[ 3 ]  = { 0, 0, 0 };
        double magnetometer_sos[ 3 ] = { 0, 0, 0 };
        // rotated accelerometers based on accelerometers and gyros only (so leveled, but not heading rotated)
        double rotated_acceleration_sum[ 3 ] = { 0, 0, 0 };
        double rotated_acceleration_sos[ 3 ] = { 0, 0, 0 };
        // for derived values of heading and heading raw
        double heading_sum = 0;
        double heading_sos = 0;
        double heading_raw_sum = 0;
        double heading_raw_sos = 0;
        // low pass vertical acceleration
        double low_pass_az_sum = 0;
        double low_pass_az_sos = 0;
        // covariances of accelerometers and gyroscopes
        double ai_gi_sum[ 3 ] = { 0, 0, 0 };
    #endif
    // wave height derived from low pass vertical acceleration
    double wave_height_sum = 0;
    double wave_height_sos = 0;

    char timestr[24];
    uint64_t sec_floor;
    uint64_t sec_hundredths;
    uint64_t  nano_epoch;
    uint64_t  nano0, nano1; 
    time_t t = time(NULL);

    // SPA 3/18/2019  These variables are for the spectral processing
    double *in, *power_spectrum, *wave_frequencies;
    double  significant_wave_height, dominant_period;
    in = fftw_alloc_real(number_of_samples);
    power_spectrum = fftw_alloc_real(number_of_samples);
    wave_frequencies = fftw_alloc_real(number_of_samples);

    // SPA 5/21/2019 set up arrays to capture the vertical accel for later processing
    double accel_vec[ 3 ];
    double *az,*low_pass_az,*wave_height;
    az = fftw_alloc_real( number_of_samples );
    low_pass_az = fftw_alloc_real( number_of_samples );
    wave_height = fftw_alloc_real( number_of_samples );

    // initialize the little LP filter to take out accel noise
    if ( rc_filter_first_order_lowpass( &acc_lp, DT, ACCEL_LP_TC ) ) return -1;
    //if ( rc_filter_butterworth_lowpass( &acc_lp, 9, DT, 2 * M_PI / 0.1 ) ) return -1;
    // filter initilization, originally included subtracting gravity, here needs to at least involve a rotation if that's to be used
    rc_filter_prefill_inputs( &acc_lp, accel_vec[ VERTICAL_AXIS ] );
   
    // set signal handler so the loop can exit cleanly
    running = 1;
    mpu_conf = rc_mpu_default_config();
    mpu_conf.i2c_bus = 1;  //for STRIDR
    mpu_conf.gpio_interrupt_pin_chip = 2;
    mpu_conf.gpio_interrupt_pin = 1;
    mpu_conf.dmp_sample_rate = INTERNAL_SAMPLE_RATE;
    mpu_conf.accel_dlpf = ACCEL_DLPF_92;
    mpu_conf.gyro_dlpf = GYRO_DLPF_92;
    mpu_conf.dmp_fetch_accel_gyro = 1;
    mpu_conf.dmp_auto_calibrate_gyro = 1;
    mpu_conf.enable_magnetometer = 1;
    mpu_conf.orient = ORIENTATION_X_DOWN;
    
    #ifdef OUTPUT_DMP
        dmp_fid = fopen( orientation_filename, "w" );
        fprintf( dmp_fid, " timestamp, Ax, Ay, Az, Lowpass Az\n" );
    #endif

    if( rc_mpu_initialize_dmp( &mpu_data, mpu_conf ) ) return -1;
    // wait for dmp to settle then start filter callback
    rc_usleep( 10000000 );
    rc_mpu_set_dmp_callback( __dmp_handler );
    
    // probably worth sleeping for a short time here as well since the filter takes some time to settle

    struct tm tm = *gmtime(&t);
    snprintf( timestr, 24, "%04d%02d%02dT%02d%02d%02d.000", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec );
 
    // Create the filename for the raw sensor data
    snprintf( fname, 99, "%ssensor_timeseries_%s.csv", output_directory, timestr );
    fid2 = fopen( fname, "w" );
    fprintf(fid2,"date - time, ax, ay, az, gx, gy, gz, mx, my, mz, heading, heading_raw, low_pass_az, rotated_ax, rotated_ay, rotated_az, roll, pitch, yaw\n");

    nano0 = rc_nanos_since_epoch();
    nano1 = nano0 + 1000000000/rate;

    #ifdef CALCULATE_STATISTICS
        // get values for shifted sums
        for ( i = 0; i < 3; i++ )
        {
            ai_shift[ i ] = mpu_data.accel[ i ];
            gi_shift[ i ] = mpu_data.gyro[ i ];
        }
    #endif

    for ( cnt = 0; cnt < number_of_samples; cnt++ )
    {
        nano0 = rc_nanos_since_epoch();
        nano1 = nano1 + 1000000000 / rate;

        rc_usleep( ( nano1 - nano0 ) / 1000 );

        t = time(NULL);
        struct tm tm = *gmtime( &t );
        nano_epoch = rc_nanos_since_epoch();
        sec_floor = floor( ( nano_epoch / pow( 10, 9 ) ) );
        sec_hundredths = ( nano_epoch / pow( 10, 7 ) ) - sec_floor * 100;

        // update sums, sums of squares, shifted sums and
        // fill accel_vec for rc_quaternion_rotate_vector_array
        for( i = 0; i < 3; i++ ) 
        {
            #ifdef CALCULATE_STATISTICS
                acceleration_sum[ i ] += mpu_data.accel[ i ];
                acceleration_shifted_sum[ i ] += mpu_data.accel[ i ] - ai_shift[ i ];
                acceleration_sos[ i ] += mpu_data.accel[ i ] * mpu_data.accel[ i ];

                rotated_acceleration_sum[ i ] += mpu_data.accel[ i ];
                rotated_acceleration_sos[ i ] += mpu_data.accel[ i ] * mpu_data.accel[ i ];

                gyro_sum[ i ] += mpu_data.gyro[ i ];
                gyro_shifted_sum[ i ] += mpu_data.gyro[ i ] - gi_shift[ i ];
                gyro_sos[ i ] += mpu_data.gyro[ i ] * mpu_data.gyro[ i ];

                magnetometer_sum[ i ] += mpu_data.mag[ i ];
                magnetometer_sos[ i ] += mpu_data.mag[ i ] * mpu_data.mag[ i ];

                ai_gi_sum[ i ] += acceleration_shifted_sum[ i ] * gyro_shifted_sum[ i ];
            #endif
            accel_vec[ i ] = mpu_data.accel[ i ];
        }
        #ifdef ROTATE_ACCEL
            rc_quaternion_rotate_vector_array( accel_vec, mpu_data.dmp_quat );
        #endif

        #ifdef CALCULATE_STATISTICS
            for ( i = 0; i < 3; i++ )
                {
                    rotated_acceleration_sum[ i ] += accel_vec[ i ];
                    rotated_acceleration_sos[ i ] += accel_vec[ i ] * accel_vec[ i ];
                }

            heading_sum += mpu_data.compass_heading;
            heading_sos += mpu_data.compass_heading * mpu_data.compass_heading;
            heading_raw_sum += mpu_data.compass_heading_raw;
            heading_raw_sos += mpu_data.compass_heading_raw * mpu_data.compass_heading_raw;
        #endif

        az[ cnt ] = accel_vec[ VERTICAL_AXIS ];
        low_pass_az[ cnt ] = acc_lp.newest_output; // * mpu_data.accel_to_ms2 * 100.0;

        #ifdef CALCULATE_STATISTICS
            low_pass_az_sum += low_pass_az[ cnt ];
            low_pass_az_sos += low_pass_az[ cnt ] * low_pass_az[ cnt ];
        #endif

        // Write out the raw sensor data
        fprintf( fid2, "%04d-%02d-%02dT%02d%02d%02d.%02d, ", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, (int)sec_hundredths );
        fprintf( fid2, "%9.4f, %9.4f, %9.4f, ",
                        mpu_data.accel[ 0 ],
                        mpu_data.accel[ 1 ],
                        mpu_data.accel[ 2 ] );
        fprintf(fid2,"%9.4f, %9.4f, %9.4f, ",
                        mpu_data.gyro[ 0 ],
                        mpu_data.gyro[ 1 ],
                        mpu_data.gyro[ 2 ] );
        fprintf(fid2,"%9.4f, %9.4f, %9.4f, ",
                        mpu_data.mag[ 0 ],
                        mpu_data.mag[ 1 ],
                        mpu_data.mag[ 2 ]);
        fprintf(fid2,"%7.3f, %7.3f, ",
                        mpu_data.compass_heading,
                        mpu_data.compass_heading_raw );
        fprintf(fid2,"%9.4f, %9.4f, %9.4f, %9.4f, ",
                        low_pass_az[ cnt ],
                        accel_vec[ 0 ],
                        accel_vec[ 1 ],
                        accel_vec[ 2 ]);
        fprintf(fid2,"%9.4f, %9.4f, %9.4f",
                        mpu_data.dmp_TaitBryan[ 0 ],
                        mpu_data.dmp_TaitBryan[ 1 ],
                        mpu_data.dmp_TaitBryan[ 2 ]);
        fprintf( fid2, "\n" );
        fflush( fid2 );
    }

    rc_mpu_power_off();
    fclose( fid2 );

    // Create the File to save the processed heights
    snprintf(fname,99,"%swave_height_%s.csv", output_directory, timestr );
    fid = fopen( fname, "w" );

    //SPA 5/21/2019 Now run the accel to height processing
    // use the low passed accel data
    az2hgt( low_pass_az, number_of_samples, rate, wave_height );
    fprintf( fid,"altitude, detrended_az\n");
    for( i = 0; i < number_of_samples; i++ )
    {
        fprintf(fid,"%9.4f, %9.4f\n",
                    wave_height[ i ],
                    low_pass_az[ i ] );
        wave_height_sum += wave_height[ i ];
        wave_height_sos += wave_height[ i ] * wave_height[ i ];

    }
    fclose(fid);

    #ifdef CALCULATE_STATISTICS
        // naive implementation of variance and co-variance for one pass calculation
        for ( i = 0; i < 3; i++ )
        {
            acceleration_sos[ i ] = ( acceleration_sos[ i ] - ( acceleration_sum[ i ] * acceleration_sum[ i ] ) / number_of_samples ) / ( number_of_samples - 1 );
            acceleration_sum[ i ] /= number_of_samples;

            rotated_acceleration_sos[ i ] = ( rotated_acceleration_sos[ i ] - ( rotated_acceleration_sum[ i ] * rotated_acceleration_sum[ i ] ) / number_of_samples ) / ( number_of_samples - 1 );
            rotated_acceleration_sum[ i ] /= number_of_samples;

            gyro_sos[ i ] = ( gyro_sos[ i ] - ( gyro_sum[ i ] * gyro_sum[ i ] ) / number_of_samples ) / ( number_of_samples - 1 );
            gyro_sum[ i ] /= number_of_samples;

            magnetometer_sos[ i ] = ( magnetometer_sos[ i ] - ( magnetometer_sum[ i ] * magnetometer_sum[ i ] ) / number_of_samples ) / ( number_of_samples - 1 );
            magnetometer_sum[ i ] /= number_of_samples;

            ai_gi_sum[ i ] = ( ai_gi_sum[ i ] - ( acceleration_shifted_sum[ i ] * gyro_shifted_sum[ i ] ) / number_of_samples ) / number_of_samples;
        }
        // heading will probably need better treatment than straight averaging
        heading_sos = ( heading_sos - ( heading_sum * heading_sum ) / number_of_samples ) / ( number_of_samples - 1 );
        heading_sum /= number_of_samples;
        heading_raw_sos = ( heading_raw_sos - ( heading_raw_sum * heading_raw_sum ) / number_of_samples ) / ( number_of_samples - 1 );
        heading_raw_sum /= number_of_samples;
        low_pass_az_sos = ( low_pass_az_sos - ( low_pass_az_sum * low_pass_az_sum ) / number_of_samples ) / ( number_of_samples - 1 );
        low_pass_az_sum /= number_of_samples;
    #endif

    wave_height_sos = ( wave_height_sos - ( wave_height_sum * wave_height_sum ) / number_of_samples ) / ( number_of_samples - 1 );
    wave_height_sum /= number_of_samples;
    for( i = 0; i < number_of_samples; i++ )
    {
        //SPA 3/18/2019  Save the heights for spectral processing
        in[ i ] = wave_height[ i ] - wave_height_sum;
    }
    waveproc( in, number_of_samples, rate, &significant_wave_height, &dominant_period,  power_spectrum, wave_frequencies );

    #ifdef CALCULATE_STATISTICS
        // output the summary statistics here
        snprintf(fname,99,"%simu_summary_%s.json", output_directory, timestr );
        fid = fopen( fname, "w" );
        fprintf( fid, "{\n" );
        fprintf( fid, "\"mean_acceleration\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    acceleration_sum[ 0 ], 
                    acceleration_sum[ 1 ],
                    acceleration_sum[ 2 ] );
        fprintf( fid, "\"var_acceleration\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    acceleration_sos[ 0 ], 
                    acceleration_sos[ 1 ],
                    acceleration_sos[ 2 ] );
        fprintf( fid, "\"mean_rotated_acceleration\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    rotated_acceleration_sum[ 0 ], 
                    rotated_acceleration_sum[ 1 ],
                    rotated_acceleration_sum[ 2 ] );
        fprintf( fid, "\"mean_gyroscope\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    gyro_sum[ 0 ], 
                    gyro_sum[ 1 ],
                    gyro_sum[ 2 ] );
        fprintf( fid, "\"var_gyroscope\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    gyro_sos[ 0 ], 
                    gyro_sos[ 1 ],
                    gyro_sos[ 2 ] );
        fprintf( fid, "\"covar_accel_gyro\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    ai_gi_sum[ 0 ], 
                    ai_gi_sum[ 1 ],
                    ai_gi_sum[ 2 ] );
        fprintf( fid, "\"mean_magnetometer\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    magnetometer_sum[ 0 ], 
                    magnetometer_sum[ 1 ],
                    magnetometer_sum[ 2 ] );
        fprintf( fid, "\"var_magnetometer\": [ %9.4f, %9.4f, %9.4f ],\n", 
                    magnetometer_sos[ 0 ], 
                    magnetometer_sos[ 1 ],
                    magnetometer_sos[ 2 ] );
        fprintf( fid, "\"mean_heading\": %5.1f,\n", 
                    heading_sum );
        fprintf( fid, "\"var_heading\": %5.1f,\n", 
                    heading_sos );
        fprintf( fid, "\"mean_heading_raw\": %5.1f,\n", 
                    heading_raw_sum );
        fprintf( fid, "\"var_heading_raw\": %5.1f,\n", 
                    heading_raw_sos );
        fprintf( fid, "\"mean_low_pass_az\": %9.4f,\n", 
                    low_pass_az_sum );
        fprintf( fid, "\"var_low_pass_az\": %9.4f,\n", 
                    low_pass_az_sos );
        fprintf( fid, "\"mean_wave_height\": %5.1f,\n", 
                    wave_height_sum );
        fprintf( fid, "\"var_wave_height\": %5.1f,\n", 
                    wave_height_sos );
        fprintf( fid, "\"significant_wave_height\": %5.1f,\n",
                    significant_wave_height );
        fprintf( fid, "\"dominant_period\": %5.1f\n",
                    dominant_period );
        fprintf( fid, "}\n" );
        fflush( fid );
        fclose( fid );
    #endif

    snprintf(fname,99,"%swave_spectrum_%s.csv",output_directory,timestr);
    fid = fopen(fname, "w");
    fprintf( fid, "\"significant_wave_height\": %5.1f\n",
            significant_wave_height );
    fprintf( fid, "\"dominant_period\": %5.1f\n",
            dominant_period );
    fprintf(fid,"wave_frequencies (Hz), PSD (m^2/Hz)\n");

    for(i=0; i<number_of_samples; i++)
    {
        if( ( wave_frequencies[ i ] < 0.5 ) & ( wave_frequencies[ i ] > 0 ) )
        {
            fprintf(fid,"%9.4f, %9.4f\n",wave_frequencies[i],power_spectrum[i]);
        }
    }
    fflush( fid );
    fclose( fid );
    return 0;
}

