#include <fftw3.h>

#include <stdio.h>
#include <string.h>
#include <math.h>
#include <malloc.h>

#define PI 3.14159
#define FREQ_LOW  0.07
#define FREQ_HI  0.4


int waveproc(double* in, int NPTS, int HZ,double* SWH, double* DWP, double* power_spectrum,double* F);
int az2hgt(double* az, int NPTS, int HZ,double* hgt);
double *hanning(int N, short itype);
int detrend(double* x, int N);

int detrend(double* x, int N)
{
        double xm=0;
        double xs=0;
        double ND ;
        int i;
        ND = N;
        
        for(i=0;i<N;i++)
        {
            xm = xm + x[i];
            if(i>0)
                xs = xs + (x[i]-x[i-1])/ND;
            
        }
        xm = xm/ND - xs*ND/2.0;
        //printf("xm = %9.6f\n",xm);
        for(i=0;i<N;i++)
            x[i] = x[i] - xm - (i-1.0)*xs;
        //    x[i] = x[i]  -xm ;
        return 0;
}

double *hanning(int N, short itype)
{
    int half, i, idx, n;
    double *w;

    w = (double*) calloc(N, sizeof(double));
    memset(w, 0, N*sizeof(double));

    if(itype==1)	//periodic function
        n = N-1;
    else
        n = N;

    if(n%2==0)
    {
        half = n/2;
        for(i=0; i<half; i++) //CALC_HANNING   Calculates Hanning window samples.
            w[i] = 0.5 * (1 - cos(2*PI*(i+1) / (n+1)));

        idx = half-1;
        for(i=half; i<n; i++) {
            w[i] = w[idx];
            idx--;
        }
    }
    else
    {
        half = (n+1)/2;
        for(i=0; i<half; i++) //CALC_HANNING   Calculates Hanning window samples.
            w[i] = 0.5 * (1 - cos(2*PI*(i+1) / (n+1)));

        idx = half-2;
        for(i=half; i<n; i++) {
            w[i] = w[idx];
            idx--;
        }
    }

    if(itype==1)	//periodic function
    {
        for(i=N-1; i>=1; i--)
            w[i] = w[i-1];
        w[0] = 0.0;
    }
    return(w);
}


int az2hgt(double* az, int NPTS, int HZ,double* hgt)
{
    //double *v; 
    double Fcutlow = 1.0/20.0;
    double Fcuthigh = 1.0/8.0;
    double dt,df;
    double *Ftapor;
    fftw_complex *Y;
    fftw_plan p,pinv;
    double *in,*FY,*v;
    int i;
    int itap1=0,itap2=0;
    in =  fftw_alloc_real(NPTS);
    v =  fftw_alloc_real(NPTS);
    Y = fftw_alloc_complex(NPTS);
    FY =  fftw_alloc_real(NPTS);

    dt = 1/(double)HZ;
    df = 1/(double)(NPTS*dt);
    //printf("dt = %f   df = %f\n",dt,df);
    
   // printf("Fcutlow= %f   Fcuthigh = %f\n",Fcutlow,Fcuthigh);
    
    
     /* create plan for forward DFT */
    p =  fftw_plan_dft_r2c_1d(NPTS, in, Y,FFTW_ESTIMATE);
    /* create plan for inverse DFT */
    pinv =  fftw_plan_dft_c2r_1d(NPTS, Y, in,FFTW_ESTIMATE);
  

   // hgt = (double*) calloc(NPTS, sizeof(double));
   // memset(hgt, 0, NPTS*sizeof(double));
   // v = (double*) calloc(NPTS, sizeof(double));
    //memset(v, 0, NPTS*sizeof(double));
    
    detrend(az,NPTS);
    
    for(i=0;i<NPTS;i++)
    {
     in[i]=az[i];
      //printf("%12.9f, %12.9f \n",az[i],hgt[i]);
    }
    
     // Run the fourier transform
    fftw_execute(p);

    //Calculate the frequencies and the filter tapor
    for(i=0;i<NPTS/2;i++)
    {
        in[i]=0.0;
        if(i<=(NPTS/2))
        {
            FY[i] = (double)i*df;
        }

        if(FY[i]<Fcutlow)
        {
           //printf("*");
            Y[i][0] = 0.0;
            Y[i][1] = 0.0;
        }

        
        //Set coef to 0 if below cut off
        if((FY[i]>Fcutlow) & (itap1==0))
        {
            itap1=i;
        }
        if((FY[i]>Fcuthigh) & (itap2==0))
        {
            itap2 = i;
        }
        
    }
 
    Ftapor = hanning( (itap2-itap1)*2 ,1);
 
 
    for(i=itap1;i<itap2;i++)
    {
         //printf("%f  %f   %f\n",Ftapor[i-itap1],Y[i][0],Y[i-itap1][0]);
         Y[i][0] = Y[i][0] * Ftapor[i-itap1];
         Y[i][1] = Y[i][1] * Ftapor[i-itap1];
    }
 
    // Run the inverse fourier transform
    fftw_execute(pinv);


    // integrate filetered accelerations to get velocity
    v[0]= 0;
    for(i=1;i<NPTS;i++)
    {
        v[i]=v[i-1] + (in[i]/(double)NPTS)*dt;
    }
    
   
     // integrate velocity to get height
    hgt[0]= 0;
    for(i=1;i<NPTS;i++)
    {
        hgt[i]=hgt[i-1] + v[i]*dt;
    }
   
     detrend(hgt,NPTS);
     
    //Clean up
    fftw_destroy_plan(p);
    fftw_destroy_plan(pinv);
    fftw_free(in);
    fftw_free(v);
    fftw_free(Y);
    fftw_free(FY);
    free(Ftapor);

    return 0;
}
 


int waveproc(double* in, int NPTS, int HZ,double* SWH, double* DWP, double* power_spectrum,double* F)
{
    fftw_complex *out;
    fftw_plan p;
    int k;
    double  dt,df,swmax,m0;

    double *Hwindow;

    /* for(k=0;k<NPTS/2;k++)
      {
        printf("%d  %6.3f\n",k,in[k]);
      }*/

    dt = 1/(double)HZ;
    df = 1/(dt*(double)NPTS);

    out = fftw_alloc_complex(NPTS);

    Hwindow = hanning(NPTS,1);


    /* create plan for forward DFT */
    p =  fftw_plan_dft_r2c_1d(NPTS, in, out,FFTW_ESTIMATE);


    // Apply the hanning window to the dataset and don't forget to compensate for loss of variance from window
    for(k=0; k<NPTS; k++)
    {
        //printf("%d  %6.3f  %6.3f\n",k,in[k],Hwindow[k]);
        in[k] = in[k]*Hwindow[k] / 0.612;

    }

    // Run the fourier transform
    fftw_execute(p);


    //Calculate the power specturm
    power_spectrum[0] = 0;  /* DC component */
    *DWP = 0;
    m0 = 0;
    swmax = 0;
    for (k = 1; k < (NPTS+1)/2; ++k)  /* (k < N/2 rounded up) */
    {

        F[k]= df*k;


        if((F[k]>FREQ_LOW) & (F[k]<FREQ_HI))
            power_spectrum[k] = 2*dt*(out[k][0]*out[k][0] + out[k][1]*out[k][1])/(NPTS);
        else
            power_spectrum[k] = 0.0;

        //Calc variance and peak period
        m0+= (power_spectrum[k] * df) ;
        if(power_spectrum[k]>swmax)
        {
            *DWP = 1/F[k];
            swmax = power_spectrum[k];
        }
    }
    /* Sig Wave Height is 4 * sqrt(variance)*/
    *SWH = 4* sqrt(m0);
    /* for(k=0;k<NPTS/2;k++)
      {
       //printf("%7.4f,%7.4e\n",F[k],power_spectrum[0]);
       if(F[k]<.5) printf("%7.4f,%7.4f\n",F[k],power_spectrum[k]);
      }

          	   printf("SWH = %6.3f   DWP = %6.3f\n",*SWH,*DWP);*/




    fftw_destroy_plan(p);
    fftw_free(out);
    free(Hwindow);
    return 0;
}
