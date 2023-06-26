#include <opencv2/imgcodecs.hpp>
#include <opencv2/videoio.hpp>
#include <opencv2/highgui.hpp>

#include <iostream>
#include <stdio.h>
#include <math.h>
#include <time.h>
#include <chrono>
#include <ctime>
#include <unistd.h>
#include <string.h>

using namespace cv;
using namespace std;
using namespace std::chrono;

namespace {
	void help( char** av )
	{
		cout << "capture opens dev/video0 and acquires images as specified by the command line arguments or its defaults." << endl
			 << "Usage:\n <runtime> <output_directory> <fps> <integration_time> <brightness>" << endl
			 << "Defaults are runtime=30 seconds, output_directory='./', fps=5, integration_time=0.0001 seconds, and brightness=0.25" << endl;
	}

	int capture_frame( VideoCapture& video_capture_object, int frame_number, const char frame_extension[ 3 ], String output_directory )
	{
		char filename[ 300 ];
		Mat frame_data;
		vector<int> compression_params;

		// time stuff
		auto frame_time( system_clock::now() );
		auto frame_time_secs( duration_cast<seconds>(frame_time.time_since_epoch() ) );
		high_resolution_clock::time_point hr_start_time, hr_stop_time;

		std::time_t frame_time_t;
		struct tm* frame_time_tm;
		char frame_time_str[ 30 ];

		frame_time_t = system_clock::to_time_t( frame_time );
		frame_time_tm = gmtime( &frame_time_t );
		strftime( frame_time_str, 
			  30,
			  "%Y%m%dT%H%M%S",
			  frame_time_tm );
		if ( video_capture_object.grab() )
		{ 
			video_capture_object.retrieve( frame_data, 0 );
		}

		if ( frame_data.empty() )
		{
			return -1;
		}
		sprintf( filename, "%s/CAMERA_%s.%03d.%s", 
				   output_directory.c_str(),
				   frame_time_str, 
				   int( ( frame_time.time_since_epoch() - frame_time_secs ).count() / 1000000 ),
			   	   frame_extension );
		cout << "Writing frame " << frame_number << " to " << filename << endl;
		if ( frame_extension == "jpg" )
		{
			compression_params.push_back( CV_IMWRITE_JPEG_QUALITY );
			compression_params.push_back( 100 );
			imwrite( filename, frame_data, compression_params );
		}
		else
		{
			imwrite( filename, frame_data );
		}
		return 0;
	}

	int process( VideoCapture& capture, int n_capture, float capture_period, String output_directory ) 
	{
		int frame_counter, frame_captured;
		clock_t start_time, fourcc_set_time;
		for ( frame_counter = 0; frame_counter < n_capture; frame_counter++ )
		{
			start_time = clock();
			// set the camera to MJPEG and capture a frame
			fourcc_set_time = clock();
			capture.set( CV_CAP_PROP_FOURCC, cv::VideoWriter::fourcc( 'M', 'J', 'P', 'G' ) );

			frame_captured = capture_frame( capture, frame_counter, "jpg", output_directory );
			if ( ( frame_counter < n_capture - 1 ) && ( capture_period != 0 ) )
			{
				usleep( ( capture_period - float( clock() - start_time ) / CLOCKS_PER_SEC ) * 1000000 );
			}
		}
		return 0;
	}
}

int main( int argc, char** argv ) {
	int process_result;
	const char* keys = 
		"{help h||}"
		"{@runtime|30|integer number of seconds to acquire data for, default = 30 seconds}"
		"{@output_directory|./|string basepath where data is stored}"
		"{@fps|1|frames per second, default = 1}"
		"{integration_time|0.0001|integration time in seconds}"
		"{contrast|0.5|contrast, 0--1}"
		"{brightness|0.25|brightness, 0--1}";

	cv::CommandLineParser parser( argc, argv, keys );
	if ( parser.has( "help" ) )
	{
		help( argv );
		return 0;
	}

	int runtime = parser.get<int>("@runtime");
	// maximum runtime is 2 minutes
	if ( runtime > 120 ) 
	{
		cout << "***WARNING*** maximum runtime is 120 seconds, you requested " << runtime << "." << endl;
		cout << "setting runtime to 120 seconds." << endl;
		runtime = 120;
	}
	String output_directory = parser.get<String>( "@output_directory" );
	float fps = parser.get<float>( "@fps" );
	float integration_time = parser.get<float>( "integration_time" );
	float contrast = parser.get<float>( "contrast" );
	float brightness = parser.get<float>( "brightness" );
	int n_frames;
	if ( ( runtime != 0 ) && ( fps <= 5.0 ) )
	{
		n_frames = int( round( float( runtime ) * fps ) );
	}
	else if ( runtime != 0 )
	{
		fps = 5.0;
		n_frames = int( round( float( runtime ) * fps ) );
	}
	else
	{
		n_frames = 1;
	}
	float time_between_frames = 1.0 / fps;

    // camera better be device 0 or something went wrong at the hardware level...
	VideoCapture capture( 0 );
	if ( !capture.isOpened() )
	{
		cerr << "***FATAL ERROR***Failed to open the oot_cam for capture." << endl;
		return 1;
	}

	cout << "=======================================" << endl;
	cout << "oot_cam opened and ready for capture..." << endl;
	capture.set( CV_CAP_PROP_FRAME_WIDTH, 1280 );
	capture.set( CV_CAP_PROP_FRAME_HEIGHT, 720 );
	cout << "---------------------------" << endl;
	cout << " - Frame size set to " << capture.get( CV_CAP_PROP_FRAME_WIDTH ) << "x" << capture.get( CV_CAP_PROP_FRAME_HEIGHT ) << endl;

	// Turning off autoexposure because it doesn't work so well when staring at the sun
	// a value of 0.75 here turns on auto exposure for nighttime/twilight use
	// or a value of 0.25 turns off auto exposure for daytime use
	capture.set( CV_CAP_PROP_AUTO_EXPOSURE, 0.25 );

	// set exposure (integration) time and brightness target to limit saturation during daytime
	capture.set( CV_CAP_PROP_EXPOSURE, integration_time );
	capture.set( CV_CAP_PROP_CONTRAST, contrast );
	capture.set( CV_CAP_PROP_BRIGHTNESS, brightness );
	
	// This will return inf if auto exposure is on, or the set exposure time
	// if auto exposure is off
	cout << " - Exposure time set to " << capture.get( CV_CAP_PROP_EXPOSURE ) << " seconds" << endl;
	cout << " - Contrast set to " << capture.get( CV_CAP_PROP_CONTRAST ) << endl;
	cout << " - Brightness set to " << capture.get( CV_CAP_PROP_BRIGHTNESS ) << endl;
	cout << "---------------------------" << endl;

	cout << "Capturing " << n_frames << " frames every " << time_between_frames << " seconds (" << fps << " fps) to " << output_directory << endl;
	process_result = process( capture, n_frames, time_between_frames, output_directory );
	cout << "=======================================" << endl;
	return process_result;
}


