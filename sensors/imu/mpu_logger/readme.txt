IMU Sampling
============

Source code:  mpu_logger.c waveproc.c

Uses the Robot Control Library to sample the IMU. Two difference modes are used, Digital Motion Processor (DMP) which 
fills a buffer and triggers a callback when the buffer is full. A lower frequency sampling loop runs in main() and records
data to the time series output file described below. In the main() sample loop accumulators are used to calculate mean and 
variance of most sensors and derived quantities.

Output files:
    imu_summary_[timestamp].json
        Reports mean, variance, and co-variance of most sensors and derived quantities. One value per acquisition period.
    sensor_timeseries_[timestamp].csv
	    Low frequency (default 6 Hz) data for each sensor and important derived quantities like heading, height deviation, significant wave height, etc.
    wave_height_[timestamp].csv
        Time series of height deviations obtained by integrating the low pass filtered and detrended vertical acceleration.
    SPC_[timestamp].csv
        Surface wave (non directional) Spectrum
        SWH =    0.02 m
        DWP =   24.38 sec
        freq (Hz), PSD (m^2/Hz)
        0.0059,    0.0000
        0.0117,    0.0000
        0.0176,    0.0000
        ......