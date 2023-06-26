#include <Wire.h>
#include <Adafruit_MPL115A2.h>

Adafruit_MPL115A2 mpl115a2;
unsigned long time1;
void setup(void) 
{
  Serial.begin(9600);

  

  mpl115a2.begin();
}

void loop(void) 
{
  float pressureKPA = 0, temperatureC = 0;   
  time1= millis();
  
  pressureKPA = mpl115a2.getPressure();  

  temperatureC = mpl115a2.getTemperature();  

   Serial.print(time1);
   Serial.print(", ");
   Serial.print(pressureKPA, 4);
   Serial.print(", ");
   Serial.println(temperatureC, 1); 



  delay(3000);
}
