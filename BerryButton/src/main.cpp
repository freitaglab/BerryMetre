// Import required libraries
#include <FS.h>
#include <LittleFS.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include "config.h" 
// config.h is the local WiFi configuration file, containing two lines:
// const char* ssid = "YOURSSID"; //Replace with your own SSID
// const char* password = "YOURSUPERSECRETPASSWORD"; //Replace with your own password

#define TARGET_IP "192.168.15.2"
#define UDP_PORT 6819
#define UDP_RECEIVE 6820

// UDP
WiFiUDP UDP;
WiFiUDP UDPReceive;

const int buttonPin = D0;
int buttonState = 0;
boolean newData = false;

const byte numChars = 255;
char receivedChars[numChars];
const char *delimiter =",";

char incomingPacket[255];
char idbuff[255];
char idchar[5];

void processUdpPackage(){
  // If packet received...
  int packetSize = UDPReceive.parsePacket();
  if (packetSize) {
    // Serial.print("Received packet! Size: ");
    // Serial.println(packetSize); 
    int len = UDPReceive.read(incomingPacket, 255);
    if (len > 0)
    {
      incomingPacket[len] = 0;
    }

   // Update device id
   char * id = strstr (incomingPacket, "id,");
   if (id) {
    Serial.println(incomingPacket);
    File file = LittleFS.open("/id.txt", "w");
    file.print(id);
    delay(1);
    file.close();

    UDP.beginPacket(TARGET_IP, UDP_PORT);
    UDP.write("Reconfigured device id: ");
    UDP.write(incomingPacket);
    UDP.endPacket();

    // Read device id configuration
    file = LittleFS.open("/id.txt", "r");
    if(!file){
      Serial.println("Failed to open file for reading");
      return;
    }
    
    while(file.available()){
      file.size();
      file.readBytes(idbuff, file.size());
      memcpy( idchar, &idbuff[3], 4 );
      idchar[4] = '\0';
      unsigned int idval;
      sscanf(idchar, "%d", &idval);
    }
    file.close();

   }
   Serial.println(incomingPacket);

   // Serial.println(incomingPacket);
   // Serial.print("Packet received: ");
   // Serial.println(packet);
  }
}

void setup(){
  unsigned long start = millis();

  Serial.begin(115200);
  Serial.println("Hello from Wemos!"); 

  pinMode(buttonPin, INPUT_PULLUP);

  // Initialize LittleFS
  if(!LittleFS.begin()){
    Serial.println("An Error has occurred while mounting LittleFS");
    return;
  }

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

  // Begin listening to UDP port
  UDPReceive.begin(UDP_RECEIVE);
  Serial.print("Listening on UDP port ");
  Serial.println(UDP_RECEIVE);

  UDP.beginPacket(TARGET_IP, UDP_PORT);
  UDP.write("Hello from Red Button Com module at ");
  UDP.write(WiFi.localIP().toString().c_str());
  UDP.endPacket();
  delay(250);

  // Read device id configuration
  File file = LittleFS.open("/id.txt", "r");
  if(!file){
    Serial.println("Failed to open file for reading");
    return;
  }
  
  UDP.beginPacket(TARGET_IP, UDP_PORT);
  while(file.available()){

    file.size();

    file.readBytes(idbuff, file.size());

    memcpy( idchar, &idbuff[3], 4 );
    idchar[4] = '\0';

    unsigned int idval;
    sscanf(idchar, "%d", &idval);

    UDP.write("Configured device id: ");
    UDP.write(idchar);

    Serial.print("Configured device id: ");
    Serial.println(idchar);

    // UDP.write(file.read());
  }
  file.close();
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
    // Serial.println("No push!");  
  } else {
    Serial.println("Push!");  
      UDP.beginPacket(TARGET_IP, UDP_PORT);
      UDP.write("id:");
      UDP.write(idchar);
      UDP.write(",");
      UDP.write("SAVE");
      UDP.endPacket();
      delay(3000);
  }
  processUdpPackage();
}