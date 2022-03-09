#include <Arduino.h>
#include <pins_arduino.h>


const byte numChars = 255;
char receivedChars[numChars];

boolean newData = false;
// Number of measurements per sequence
const int msr = 26;

unsigned int dwellTime = 25;
const int postLoopDelay = 5;

// unsigned int dtval = 100;
char dtchar[5];

// high end dye cell
// const int dwellTime = 30;
// const int postLoopDelay = 0;

// Buffer for serial communication
char sbuff[255]; 
const unsigned int MAX_MESSAGE_LENGTH = 256;

// 13 is dummy pin and should be left free
const int pinSequence[msr][6] =  {{12,  11, A5, 13, 13,	13},   // 0: 89.8
                                  {12,  13, 13, 11, 11,	10},   // 1: 117.4
                                  {11,  10, 12, 13, 13,	7},    // 258.8
                                  {11,  7,  13, 10, 10,	9},     // 324.6
                                  {10,  9,  11, 7,  8,	13},     // 443.1
                                  {8,   9,  10, 13, 7,	13},     // 4: 594.5
                                  {7,   9,  8,	13, 6,	13},     // 5: 678.3
                                  {6,   9,  7,	13, 10,	13},     // 6: 758.5
                                  {10,  13, 6,  9,  9,	5},    // 802
                                  {9,   5,  10, 13, 7,	8},     // 8: 817.1
                                  {7,   8,  9,  5,  9,	13},     // 7: 880.1
                                  {9,   13, 7,	8,  8,	5},    // 9: 990
                                  {8,   5,  9,	13, 7,	6},     // 10: 1128.9
                                  {7,   6,  8,	5,  8,	13},     // 11: 1294.5
                                  {8,   13, 7,	6,  7,	13},    // 12: 1488
                                  {7,   13, 8,	13, 6,	13},    // 13: 2154
                                  {6,   3,  7,	13, 13,	13},     // 14: 2892
                                  {6,   13, 13, 3,  3,	5},    // 15: 3244
                                  {3,   5,  6,	13, 13,	13},     // 16: 3978.7
                                  {5,   13, 3,	5,  4,	13},    // 17: 4677
                                  {4,   2,  5,	13, 13,	13},     // 18: 5258.1
                                  {4,   13, 13, 2,  3,	2},    // 19: 5502
                                  {3,   2,  4,	13, 13,	13},     // 20: 21760.3
                                  {3,   13, 13, 2,  2,	13},    // 21: 26650
                                  {2,   13, 3,  13, 13,	13},    // 22: 118600
                                  {13,  13, 2,  13, 13	,13}};   // VOC, internal 100MOhm

float analog_value;
const int numPins = 11; 
float analog_values[msr];
int count = 0;

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
        Serial.println(receivedChars);
      // check if dwell time has been requested
      if (receivedChars[0] == 'd'  && receivedChars[1] == 't')
      {
        Serial.println("Dwell time received: ");
        memcpy(dtchar, &receivedChars[3], 4 );
        dtchar[4] = '\0';
        sscanf(dtchar, "%d", &dwellTime);
        Serial.println(dwellTime);
      }
        newData = false;
    }
}

void setup() {
  // Startup delay to wait for the Wemos

  Serial.begin(115200);
  // Wait until serial port is opened
  while (!Serial) { delay(1); }

  // Serial1.begin(115200);
  // while (!Serial1) { delay(1); }

  Serial.flush();

  Serial.println("<BerryMetre Simple Solar Sim>");
  Serial.println("<Waiting for Wemos to be ready>");
  for (int i=0; i<10; i++)
  {
    Serial.print(".");
    delay(1000);
  }
  Serial.println();

  for (int i=0; i<numPins; i++)
  {
    pinMode(i+2, OUTPUT);
    digitalWrite(i+2, LOW);
  }
  pinMode(A5, OUTPUT);
  // We start with a forward scan
  digitalWrite(A5, LOW);
  delay(1000);

  // Request dwell time from D1 mini
  Serial.println("<rqdt>");

}

void measure(int valPos)
{
  analog_value = analogRead(A2);
  analog_value *= 5.0;
  analog_value /= 1024;
  // Serial.print(analog_value,3);
  analog_values[valPos] = analog_value;
  // Serial.print(valPos);
  // Serial.print(" ");
}

void backwardscan()
{
  digitalWrite(A5, LOW);

  // Serial.println("Backward scan");
  for (int i=msr; i>0; i--)
  {
      digitalWrite(pinSequence[i-1][0], HIGH);
      digitalWrite(pinSequence[i-1][1], HIGH);
      digitalWrite(pinSequence[i-1][4], LOW);
      digitalWrite(pinSequence[i-1][5], LOW);
      delay(dwellTime);
      measure(i-1);
  }
  // Backwardscan ends with setting cell to Isc
  digitalWrite(A5, HIGH);
  // Use print time for a bit of dwelling
  // Serial.println();
}

void forwardscan()
{
  // Serial.println("Forward scan");
  for (int i=0; i<msr; i++)
  {
      digitalWrite(pinSequence[i][0], HIGH);
      digitalWrite(pinSequence[i][1], HIGH);
      digitalWrite(pinSequence[i][2], LOW);
      digitalWrite(pinSequence[i][3], LOW);
      delay(dwellTime);
      measure(i);
  }

  // Back to 0
  digitalWrite(A5, HIGH);
  delay(dwellTime);
  // Serial.println();
}

void activate(int pos1, int pos2, int valPos)
{
  digitalWrite(pos1, HIGH);
  digitalWrite(pos2, HIGH);

  delay(dwellTime);
  measure(valPos);
  delay(2);

  digitalWrite(pos1, LOW);
  digitalWrite(pos2, LOW);
  delay(dwellTime);
}



void loop() {
  recvWithStartEndMarkers();
  evaluateNewData();
  delay(1);

  // Sequence 1 start: Forward scan with jump
  for (int i = 0; i < msr; i++)
  {
    activate(pinSequence[i][0], pinSequence[i][1], i);
  }

  Serial.print("<");
  for (int i = 0; i<msr; i++)
  {
    Serial.print(analog_values[i],4);
    Serial.print(",");
  }
  Serial.print(count);
  count++;
  if (count == 10)
    count = 0;

  Serial.print(">");
  Serial.println();
  delay(postLoopDelay);
  // Sequence 1 end

  // Sequence 2 start - forward to backward - requires optimization
  // forwardscan();
  // for (int i = 0; i<msr; i++)
  // {
  //   Serial.print(analog_values[i],4);
  //   Serial.print(",");
  // }
  // Serial.print(count);
  // count++;
  // if (count == 10)
  //   count = 0;
  // Serial.println();
  // // Serial.println();

  // backwardscan();
  // for (int i = 0; i<msr; i++)
  // {
  //   Serial.print(analog_values[i],4);
  //   Serial.print(",");
  // }
  // Serial.print(count);
  // count++;
  // if (count == 10)
  //   count = 0;
  // Serial.println();

  // Serial.println();
  // delay(postLoopDelay);
  // Sequence 2 end

  // Sequence 3 start - forward only
  // forwardscan();
  // for (int i = 0; i<msr; i++)
  // {
  //   Serial.print(analog_values[i],4);
  //   Serial.print(",");
  // }
  // Serial.print(count);
  // count++;
  // if (count == 10)
  //   count = 0;
  // Serial.println();
  // // Serial.println();
  // delay(postLoopDelay);
  // Sequence 3 end
}

