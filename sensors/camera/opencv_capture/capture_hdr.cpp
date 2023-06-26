#include "opencv2/photo.hpp"
#include "opencv2/imgcodecs.hpp"
#include "opencv2/videoio.hpp"
#include "opencv2/highgui.hpp"

#include <vector>
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
		cout << "capture_hdr opens dev/video0 and acquires an exposure sequence of images for HDR processing using the Mertens fusion algorithm." << endl
			 << "Usage:\n <runtime> <output_directory> <fps>" << endl
			 << "Defaults are runtime=30 seconds, output_directory='./', fps=1" << endl;
	}

        void configure_heartbeat_led(bool enabled)
        {
                string state;
                if (enabled == true) state = "heartbeat";
                else state = "none";
                string command = "echo " + state + " > /sys/class/leds/stridr:red:usr0/trigger";
                const char *cmd = command.c_str();
                system(cmd);
        }

	int capture_hdr_frame( VideoCapture& video_capture_object, int frame_number, const char frame_extension[ 3 ], String output_directory )
	{
		char filename[ 300 ];
        	Mat this_frame;
	        Mat mertens_fusion;
		vector<Mat> frame_data;
		vector<int> compression_params;
		int buffer_count;
	        float exposure_increment;

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

		// disable annoying red LED heartbeat
		configure_heartbeat_led(false);
	        for ( exposure_increment = 1.0; exposure_increment < 6.0; exposure_increment++ )
        	{
	            // read frames to clear the buffer and obtain the most recent image with the new exposure time
        	    video_capture_object.set( CV_CAP_PROP_EXPOSURE, exposure_increment / 5000.0 );
	            cout << " - Exposure time set to " << video_capture_object.get( CV_CAP_PROP_EXPOSURE ) << " seconds" << endl;
        	    for ( buffer_count = 0; buffer_count < 4; buffer_count++ )
	            {
        	        video_capture_object.grab();
	            }
        	    if ( video_capture_object.grab() )
	            { 
        	        video_capture_object.retrieve( this_frame, 0 );
                	frame_data.push_back( this_frame );
	            }
        	}
		// re-enable annoying red LED heartbeat
		configure_heartbeat_led(true);

	        Ptr<MergeMertens> mertens_processor = createMergeMertens();
        	mertens_processor->process( frame_data, mertens_fusion );
		sprintf( filename, "%s/CAMERA_HDR_%s.%03d.%s", 
				   output_directory.c_str(),
				   frame_time_str, 
				   int( ( frame_time.time_since_epoch() - frame_time_secs ).count() / 1000000 ),
			   	   frame_extension );
		cout << "Writing frame " << frame_number << " to " << filename << endl;
		if ( frame_extension == "jpg" )
		{
			compression_params.push_back( CV_IMWRITE_JPEG_QUALITY );
			compression_params.push_back( 100 );
			imwrite( filename, mertens_fusion * 255, compression_params );
		}
		else
		{
			imwrite( filename, mertens_fusion * 255 );
		}
		return 0;
	}

	int capture_ae_frame( VideoCapture& video_capture_object, int frame_number, const char frame_extension[ 3 ], String output_directory )
	{
		char filename[ 300 ];
	        Mat this_frame;
		vector<int> compression_params;
		int buffer_count;

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

		// disable annoying red LED heartbeat
		configure_heartbeat_led(false);
		for ( buffer_count = 0; buffer_count < 4; buffer_count++ )
		{
		    video_capture_object.grab();
		}
		if ( video_capture_object.grab() )
		{ 
		    video_capture_object.retrieve( this_frame, 0 );
		}
		// re-enable annoying red LED heartbeat
		configure_heartbeat_led(true);

		sprintf( filename, "%s/CAMERA_AE_%s.%03d.%s", 
				   output_directory.c_str(),
				   frame_time_str, 
				   int( ( frame_time.time_since_epoch() - frame_time_secs ).count() / 1000000 ),
			   	   frame_extension );
		cout << "Writing frame " << frame_number << " to " << filename << endl;
		if ( frame_extension == "jpg" )
		{
			compression_params.push_back( CV_IMWRITE_JPEG_QUALITY );
			compression_params.push_back( 100 );
			imwrite( filename, this_frame, compression_params );
		}
		else
		{
			imwrite( filename, this_frame );
		}
		return 0;
	}

	int process_hdr( VideoCapture& capture, int n_capture, float capture_period, String output_directory ) 
	{
		int frame_counter, frame_captured;
		clock_t start_time;
		for ( frame_counter = 0; frame_counter < n_capture; frame_counter++ )
		{
			start_time = clock();

			frame_captured = capture_hdr_frame( capture, frame_counter, "jpg", output_directory );
			if ( ( frame_counter < n_capture - 1 ) && ( capture_period != 0 ) )
			{
				usleep( ( capture_period - float( clock() - start_time ) / CLOCKS_PER_SEC ) * 1000000 );
			}
		}
		return 0;
	}

	int process_ae( VideoCapture& capture, int n_capture, float capture_period, String output_directory ) 
	{
		int frame_counter, frame_captured;
		clock_t start_time;
		for ( frame_counter = 0; frame_counter < n_capture; frame_counter++ )
		{
			start_time = clock();

			frame_captured = capture_ae_frame( capture, frame_counter, "jpg", output_directory );
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
		"{contrast|0.5|contrast, 0--1}"
		"{brightness|0.5|brightness, 0--1}"
		"{backlight|0|backlight compensation, 0, 1, 2}";

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
	float contrast = parser.get<float>( "contrast" );
	float brightness = parser.get<float>( "brightness" );
	int backlight = parser.get<int>( "backlight" );
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
	capture.set( CV_CAP_PROP_FOURCC, cv::VideoWriter::fourcc( 'M', 'J', 'P', 'G' ) );

	// set exposure (integration) time and brightness target to limit saturation during daytime
	capture.set( CV_CAP_PROP_CONTRAST, contrast );
	capture.set( CV_CAP_PROP_BRIGHTNESS, brightness );
	capture.set( CV_CAP_PROP_BACKLIGHT, backlight );
	
	// This will return inf if auto exposure is on, or the set exposure time
	// if auto exposure is off
	cout << " - Contrast set to " << capture.get( CV_CAP_PROP_CONTRAST ) << endl;
	cout << " - Brightness set to " << capture.get( CV_CAP_PROP_BRIGHTNESS ) << endl;
	cout << " - Backlight compensation set to " << capture.get( CV_CAP_PROP_BACKLIGHT ) << endl;
	cout << "---------------------------" << endl;

	cout << "Capturing frames for HDR processing" << output_directory << endl;
	cout << "===================================" << endl;
	process_result = process_hdr( capture, n_frames, time_between_frames, output_directory );

	cout << "Capturing frames using auto exposure" << output_directory << endl;
	cout << "====================================" << endl;
	capture.set( CV_CAP_PROP_AUTO_EXPOSURE, 0.75 );
	process_result = process_ae( capture, n_frames, time_between_frames, output_directory );

	capture.release();
	cout << "================ Done =================" << endl;
	return process_result;
}



