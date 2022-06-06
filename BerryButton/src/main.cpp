// Import required libraries
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include "config.h" 
// config.h is the local WiFi configuration file, containing two lines:
// const char* ssid = "YOURSSID"; //Replace with your own SSID
// const char* password = "YOURSUPERSECRETPASSWORD"; //Replace with your own password

#define TARGET_IP "192.168.15.2"
#define UDP_PORT 6819

// UDP
WiFiUDP UDP;

const int buttonPin = D0;
int buttonState = 0;

void setup(){
  unsigned long start = millis();

  Serial.begin(115200);
  Serial.println("Hello from Wemos!"); 

  pinMode(buttonPin, INPUT_PULLUP);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    // Serial.println("Connecting to WiFi..");
  }

  // Connected to WiFi
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  delay(250);

  UDP.beginPacket(TARGET_IP, UDP_PORT);
  UDP.write("Hello from Red Button Com module at ");
  UDP.write(WiFi.localIP().toString().c_str());
  UDP.endPacket();
  delay(250);

  Serial.print("Startup time: ");
  Serial.println(millis() - start);
}
 
void loop(){
  // read the state of the pushbutton value:
  buttonState = digitalRead(buttonPin);

  // check if the pushbutton is pressed. If it is, the buttonState is HIGH:
  if (buttonState == HIGH) {
    Serial.println("No push!");  
  } else {
    Serial.println("Push!");  
      UDP.beginPacket(TARGET_IP, UDP_PORT);
      UDP.write("SAVE");
      UDP.endPacket();
      delay(3000);
  }
}