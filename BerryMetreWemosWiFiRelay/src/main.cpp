// Import required libraries
#include <FS.h>
#include <LittleFS.h>
#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <WiFiUdp.h>
#include "config.h" 
// config.h is the local WiFi configuration file, containing two lines:
// const char* ssid = "YOURSSID"; //Replace with your own SSID
// const char* password = "YOURSUPERSECRETPASSWORD"; //Replace with your own password

#define TARGET_IP "192.168.15.2"
#define UDP_PORT 6819
#define UDP_RECEIVE 6820

const unsigned int MAX_MESSAGE_LENGTH = 255;

int count = 48; // ASCII 0

// UDP
WiFiUDP UDP;
WiFiUDP UDPReceive;

char incomingPacket[255];
char dtbuff[255];
char dtchar[5];

const int ledPin = 2;
String ledState;

const byte numChars = 255;
char receivedChars[numChars];
const char *delimiter =",";

float uvalues[26] = {0.0};
float ivalues[26] = {0.0};
float pvalues[26] = {0.0};
float res[26] = {89.8+20.0,117.4,258.8,324.6,443.1,594.5,678.3,758.5,802,817.1,880.1,990,1128.9,1294.5,1488,2154,2892.0,3244,3978.7,4677,5258.1,5502,21760.3,26650,118600,100000000};

boolean newData = false;

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;
 
    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

void evaluateNewData() {
    if (newData == true) {
      // Serial.println(receivedChars);

      // check if dwell time has been requested
      if (receivedChars[0] == 'r'  && receivedChars[1] == 'q'  && receivedChars[2] == 'd'  && receivedChars[3] == 't')
      {
        UDP.beginPacket(TARGET_IP, UDP_PORT);
        UDP.write("Dwell time request received!");
        UDP.endPacket();
        Serial.print("<dt,");
        Serial.print(dtchar);
        Serial.println(">");
      }
      else
      {
        UDP.beginPacket(TARGET_IP, UDP_PORT);
        UDP.write(receivedChars);
        UDP.endPacket();
      }

      int pos = 0;
      char * token;
      token = strtok(receivedChars, delimiter);
      while (token != NULL && pos < 26)
      {
        uvalues[pos] = String(token).toFloat();
        ivalues[pos] = uvalues[pos]*1000.0/res[pos];
        pvalues[pos] = uvalues[pos]*ivalues[pos];
        // Serial.print(uvalues[pos],4);
        // Serial.print(",");
        token = strtok(NULL, delimiter);
        pos++;
      }
      // Serial.println();
      newData = false;
    }
}

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

   char * p = strstr (incomingPacket, "dt,");
   if (p) {
    // Serial.println("<DT configuration value found, updating flash and sending to Arduino...>");

    // Serial.print("<dt,");
    // Serial.print(dtchar);
    // Serial.println(">");

    Serial.println(incomingPacket);
    File file = LittleFS.open("/dt.txt", "w");
    file.print(p);
    delay(1);
    file.close();

   } else {
    Serial.println(incomingPacket);
    // Serial.println("Other package content");
   }
    // Serial.println(incomingPacket);

    // Serial.print("Packet received: ");
    // Serial.println(packet);
  }
}

// Create AsyncWebServer object on port 80
AsyncWebServer server(80);

// Replaces placeholder with LED state value
String processor(const String& var){
  Serial.println(var);
  if(var == "GPIO_STATE"){
    if(digitalRead(ledPin)){
      ledState = "OFF";
    }
    else{
      ledState = "ON";
    }
    Serial.print(ledState);
    return ledState;
  }
  return String();
}

// Replaces placeholder with LED state value
String valuereplace(const String& var){
  for (int i=0; i<26; i++)
  {
      String ucmp = "UVAL_" + String(i+1);
      if (var == ucmp)
        return String(uvalues[i]);
      String icmp = "IVAL_" + String(i+1);
      if (var == icmp)
        return String(ivalues[i]);
      String pcmp = "PVAL_" + String(i+1);
      if (var == pcmp)
        return String(pvalues[i]);
  }
 
  return String();
}

void setup(){
  unsigned long start = millis();

  Serial.begin(115200);
  Serial.println("Hello from Wemos!"); 

  pinMode(ledPin, OUTPUT);

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

// Begin listening to UDP port
  UDPReceive.begin(UDP_RECEIVE);
  Serial.print("Listening on UDP port ");
  Serial.println(UDP_RECEIVE);

  // Connected to WiFi
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  delay(250);

  UDP.beginPacket(TARGET_IP, UDP_PORT);
  UDP.write("Hello from BerryMetre Com module at ");
  UDP.write(WiFi.localIP().toString().c_str());
  UDP.endPacket();
  delay(250);

  // Read dwell time configuration
  File file = LittleFS.open("/dt.txt", "r");
  if(!file){
    Serial.println("Failed to open file for reading");
    return;
  }
  
  UDP.beginPacket(TARGET_IP, UDP_PORT);
  while(file.available()){

    file.size();

    file.readBytes(dtbuff, file.size());

    memcpy( dtchar, &dtbuff[3], 4 );
    dtchar[4] = '\0';

    unsigned int dtval;
    sscanf(dtchar, "%d", &dtval);

    UDP.write("Configured dwell time: ");
    UDP.write(dtchar);

    // UDP.write(file.read());
  }
  file.close();
  UDP.endPacket();

  // Route for root / web page
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/index.html", String(), false, processor);
  });
  
  // Route to load style.css file
  server.on("/d3.min.js", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/d3.min.js", "text/javascript");
  });

  server.on("/own.csv", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/own.csv", String(), false, valuereplace);
  });

  server.on("/led.html", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/led.html", String(), false, processor);
  });

  // Route to set GPIO to HIGH
  server.on("/led2on", HTTP_GET, [](AsyncWebServerRequest *request){
    digitalWrite(ledPin, LOW);    
    request->send(LittleFS, "/led.html", String(), false, processor);
  });
  
  // Route to set GPIO to LOW
  server.on("/led2off", HTTP_GET, [](AsyncWebServerRequest *request){
    digitalWrite(ledPin, HIGH);    
    request->send(LittleFS, "/led.html", String(), false, processor);
  });

  // Start server
  server.begin();
  Serial.print("Startup time: ");
  Serial.println(millis() - start);
}
 
void loop(){
  recvWithStartEndMarkers();
  evaluateNewData();
  processUdpPackage();
}