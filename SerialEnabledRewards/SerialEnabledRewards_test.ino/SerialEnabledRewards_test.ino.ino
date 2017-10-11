/* IR detectection using interrupt pins for the sensor shield setup.
    It sends an output the serial monitor and to the pumps.
    A well is active only if serial input allows it.

  Serial Commands:
  a -> activate all wells
  w -> activate individual well
  d -> deactivate individual well
  s -> check status of all wells
  r -> reset. deactivates all wells
  p -> select pump to turn-on
  c -> change pump duration
  z -> select cue {1,2,3,4}
  y -> turn off cue.

  Alex Gonzalez
  Updated: 9/21/17
*/


// CUE library
#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
#include <avr/power.h>
#endif

/* Program constants.
*/
const long BAUD_RATE = 115200; // baud rate for serial communication. must match contro script
const long DETECT_TIME_THR  = 50; // in ms
const bool Pump_ON = LOW; // LOW activates the pump
const bool Pump_OFF = HIGH; // HIGH deactivates the pump.
const int nWells = 6; // number of reward wells

/*  ***************************
    Declaration of Arduino Pins
*/
// PINs for CUE signals output and control.
const int CUEs1_PIN = 46;
const int CUEs2_PIN = 47;

// TTL Well LED Pins
const int TTL_LED_Pins[6] = {4, 5, 6, 7, 8, 9};

// TTL WELL IR Detect Pins
const int TTL_IR_Pins[6] = {10, 11, 12, 26, 27, 28};

// TTL CUE Code Pins
const int TTL_CUE_Pins[4] = {29, 30, 31, 32};

// TTL Reward Delivered Pin (one pump activated)
const int TTL_RD_Pin = 33;

// Pins for the Pump outputs
const int Pumps_Pins[6] = {34, 35, 36, 37, 38, 39};

// Interrupt Pins for the input IR detects
const int Well_IR_Pins[6] = {2, 3, 21, 20, 19, 18};

// LED outout pins LEDs
const int Well_LED_Pins[6] = {40, 41, 42, 43, 44, 45};

// Default values for pump durations
//const long Pump_ON_Default[6]   = {12, 12, 15, 15, 15, 15};
//long Pump_ON_DUR[6]    = {12, 12, 15, 15, 15, 15};
const long Pump_ON_Default[6]   = {15, 15, 18, 18, 18, 18};
long Pump_ON_DUR[6]    = {15, 15, 18, 18, 18, 18};
// in ms (100ms=0.25ml; 40ms=0.1ml)
/* **********************************
   End of Declaration of Arduino Pins
*/
// Setup of Neopixel:
Adafruit_NeoPixel NeoPix = Adafruit_NeoPixel(1, CUEs2_PIN, NEO_GRB + NEO_KHZ800);
const uint32_t  NP_blueviolet = NeoPix.Color(150, 0, 255);
const uint32_t  NP_green = NeoPix.Color(0, 100, 0);
const uint32_t  NP_off = NeoPix.Color(0, 0, 0);

// Cue parameters
const int nCues = 6;
const uint32_t  CUE_Colors[2] = {NP_blueviolet, NP_green}; // array for NP colors
const float CUE_Freqs[3] = {1.67, 3.85, 0};
// half cycles of CUE_Freqs in ms: HC = (1/F)/2*1000
const long CUE_HalfCycles[3] = {300, 130, 0};

// cue state variables
uint32_t  ActiveCueColor = NP_off;
float ActiveCUE_Freq = 0;
long ActiveCUE_HalfCycle = 0;
bool ActiveCUE_UP = false;
int ActiveCUE_ID = -1;

// Cue timers
unsigned long CUE_Timer;      // time ref for pump on
unsigned long CUE_TimeRef;

// Serial State Variable:
bool SerialState = false;

// Well State Variables:
bool Well_IR_State[nWells]; // state variable for the wells IR interrupts
bool Well_Detect_State[nWells]; // state variable for wells IRs that passed threshold.
bool Well_LED_State[nWells]; // variable LED indicating on/off
bool Well_Active_State[nWells]; // state variable indicating active well
bool Pump_State[nWells]; // Pump: on/off

// Time references
unsigned long Well_Active_TimeRef[nWells]; // time reference for LED on
unsigned long Well_Active_Timer[nWells];   // timer indicating how long LED has been on
unsigned long Well_IR_TimeRef[nWells];  // time reference: for IR detection
unsigned long Well_IR_Timer[nWells];    // timer for how long IR has been on.
unsigned long PumpTimeRef[nWells];      // time ref for pump on
unsigned long PumpTimer[nWells];        // timer for how long pump has been on

// Event codes
char RR[] = "RR"; // reward
char DD[] = "DD"; // detection
char AW[] = "AW"; // actived well
char DW[] = "DW"; // deactivated well (usually after detection)
char CA[] = "CA"; // cue on.
char CD[] = "CD"; // cue off/

// Setup
void setup() {
  //  state variables for the wells & time references initiation
  for (int ii = 0; ii < nWells; ii++) {

    Well_IR_State[ii] = false;
    Well_Detect_State[ii] = false;
    Well_LED_State[ii] = false;
    Pump_State[ii] = false;

    Well_Active_TimeRef[ii] = 15000UL;
    Well_IR_TimeRef[ii] = 15000UL;
    PumpTimeRef[ii] = 15000UL;

    Well_Active_Timer[ii] = 0;
    PumpTimer[ii] = 0;
    Well_IR_Timer[ii] = 0;
  }

  // LEDs
  for (int ii = 0; ii < nWells; ii++) {
    // set LED pins to outputs and to low
    pinMode(Well_LED_Pins[ii], OUTPUT);
    digitalWrite(Well_LED_Pins[ii], LOW);

    // IR inputs
    pinMode(Well_IR_Pins[ii], INPUT_PULLUP);

    // Pump outputs
    pinMode(Pumps_Pins[ii], OUTPUT);
    digitalWrite(Pumps_Pins[ii], HIGH);
  }
  // Attach interrupts independently
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[0]), IR_Detect1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[1]), IR_Detect2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[2]), IR_Detect3, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[3]), IR_Detect4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[4]), IR_Detect5, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[5]), IR_Detect6, CHANGE);

  // Neopixel setup:
  NeoPix.begin();
  NeoPix.setBrightness(90);
  NeoPix.show();

  delay(500);
  Serial.begin(BAUD_RATE);
  Serial.println("<");
  Serial.println("<Initiation complete. Waiting for a detection.");
  Serial.print(">");
}

//Main
void loop() {
  if (Serial) {
    if (not SerialState) {
      SerialState = true;
    }
    // Check serial input.
    ProcessInput();
    // Process the wells.
    for (int well = 0; well < nWells; well++) {
      WellDetectThrCheck(well);
      // if well is active, check to deliver reward
      if  (Well_Active_State[well] == true) {
        if (Pump_State[well] == false && Well_Detect_State[well] == true) {
          Deliver_Reward(well);
          DeActivateWell(well);
        }
      }
      // turn off pump after Pump_ON_DUR duration
      if (Pump_State[well] == true) {
        PumpTimer[well] = millis() - PumpTimeRef[well];
        if (PumpTimer[well] >= Pump_ON_DUR[well]) {
          TurnOFFPump(well);
          Serial.print("<Reward Delivered to Well # ");
          Serial.println(well + 1);
          Serial.print(">\n");
          sendEventCode(RR, well + 1);
        }
      }
    }

    // Process the cue if not constant.
    if (ActiveCUE_ID >= 0 & ActiveCUE_ID <= 3) {
      CUE_Timer = millis() - CUE_TimeRef;
      if (CUE_Timer > ActiveCUE_HalfCycle) {
        if (ActiveCUE_UP) {
          ActiveCUE_UP = false;
          ChangeCueColor(NP_off);
        }
        else {
          ActiveCUE_UP = true;
          ChangeCueColor(ActiveCueColor);
        }
      }
    }
  } else if (SerialState) {
    SerialState = false;
    reset_states();
    TurnCueOff();
  }
}

/*************************************
  ISR routines for IR well detection
**************************************/
void IR_Detect1() {
  IR_Detect_ReportChange(0);
}
void IR_Detect2() {
  IR_Detect_ReportChange(1);
}
void IR_Detect3() {
  IR_Detect_ReportChange(2);
}
void IR_Detect4() {
  IR_Detect_ReportChange(3);
}
void IR_Detect5() {
  IR_Detect_ReportChange(4);
}
void IR_Detect6() {
  IR_Detect_ReportChange(5);
}

/*************************************
  IR detection routines
**************************************/
// Detection state
void IR_Detect_ReportChange(int well) {
  if (digitalRead(Well_IR_Pins[well]) == LOW) {
    Well_IR_State[well] = true;
    Well_IR_TimeRef[well] = millis();
    Well_IR_Timer[well] = 0;
  } else {
    Well_IR_State[well] = false;
    Well_Detect_State[well] = false;
    ResetDetectTimer(well);
  }
}

// Detection Threshold
void WellDetectThrCheck(int well) {
  if (Well_Detect_State[well] == false) {
    if (Well_IR_State[well] == true) {
      Well_IR_Timer[well] = millis() - Well_IR_TimeRef[well];
      if (Well_IR_Timer[well] >= DETECT_TIME_THR) {
        Well_Detect_State[well] = true;
        ResetDetectTimer(well);
        Serial.print("<Detection on Well # ");
        Serial.println(well + 1);
        Serial.print(">\n");
        sendEventCode(DD, well + 1);
      }
    }
  }
}

// Reset IR Timer
void ResetDetectTimer(int well) {
  Well_IR_TimeRef[well] = 15000UL;
  Well_IR_Timer[well] = 0;
}

/****************************************
      Serial IO processing.
*****************************************/
// Process serial command input.
void ProcessInput() {
  if (Serial.available()) {
    char inchar = Serial.read();
    switch (inchar) {
      // well input
      case 'a':
        ActivateAllWells();
        break;
      case 'w':
        SelectWellToActive();
        break;
      case 'l':
        // turns LED on for active goal well(s)
        // led is on for home/decision wells
        Well_LED_ON();
        break;
      case 'd':
        SelectWellToDeActive();
        break;
      case 'p':
        SelectPumpToTurnOn();
        break;
      case 'c':
        ChangePumpOnDur();
        break;
      case 's':
        print_states();
        break;
      case 'r':
        reset_states();
        Serial.print("<All wells inactivated.");
        break;
      case 'z':
        SelectCueOn();
        break;
      case 'y':
        TurnCueOff();
        break;
      default:
        Serial.println("<IncorrectSuffix");
        Serial.print(">\n");
        break;
    }
  }
}

// Read serial number
int SerialReadNum() {
  unsigned long intimer = millis();
  while (intimer >= (millis() - 5000)) {
    if (Serial.available()) {
      int num = Serial.read();
      num = num - 49;
      if (num >= 0 && num <= 9) {
        return num;
      }
      else {
        Serial.print("<Ard. Invalid Input, expected int [0-9].");
        Serial.println(num);
        Serial.print(">\n");
        return -1;
      }
    }
  }
  Serial.println("<\nArd. Timed out to input number.");
  Serial.print(">\n");
  return -1;
}

// send event code
void sendEventCode(char* code, int num) {
  char str[10];
  sprintf(str, "<EC_%s%d", code, num);
  Serial.println(str);
  Serial.println(">\n");
}

/****************************************
              Cue Control
*****************************************/
int SelectCueOn() {
  int cue = SerialReadNum();
  if (cue >= 0 && cue <= nCues) {
    ActiveCUE_ID = cue;
    sendEventCode(CA, cue + 1);
    Serial.print("<Ard. Activated Cue #");
    Serial.println(cue + 1);
    Serial.print(">\n");
  }
  else {
    ActiveCUE_ID = -1;
    Serial.println("<\nArd. Invalid cue number.");
    Serial.print(">\n");
  }
  SetCueParams(ActiveCUE_ID);
  return ActiveCUE_ID;
}

void TurnCueOff() {
  sendEventCode(CD, ActiveCUE_ID + 1);
  SetCueParams(-1);
  CUE_TimeRef = 15000L;
  CUE_Timer   = 0;
}

void SetCueParams(int CueNum) {
  switch (CueNum) {
    // color 1
    case 0:
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[0];
      ActiveCUE_HalfCycle = CUE_HalfCycles[0];
      break;
    case 1:
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[1];
      ActiveCUE_HalfCycle = CUE_HalfCycles[1];
      break;
    // color 2
    case 2:
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[0];
      ActiveCUE_HalfCycle = CUE_HalfCycles[0];
      break;
    case 3:
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[1];
      ActiveCUE_HalfCycle = CUE_HalfCycles[1];
      break;
    // constant colors
    case 4:
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[2];
      ActiveCUE_HalfCycle = CUE_HalfCycles[2];
      break;
    case 5:
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[2];
      ActiveCUE_HalfCycle = CUE_HalfCycles[2];
      break;
    default:
      ActiveCUE_ID = -1;
      ActiveCueColor = NP_off;
      ActiveCUE_Freq = 0;
      ActiveCUE_HalfCycle = 0;
      break;
  }
  ChangeCueColor(ActiveCueColor);
}
void ChangeCueColor(uint32_t col) {
  if (col == NP_off) {
    NeoPix.clear();
  } else {
    NeoPix.setPixelColor(0, col);
  }
  NeoPix.show();
  CUE_TimeRef = millis();
  CUE_Timer   = 0;

}

/****************************************
      Pump/Reward Control
*****************************************/
int SelectPumpToTurnOn() {
  int well = SerialReadNum();
  if (well >= 0 && well <= 5) {
    TurnOnPump(well);
    Serial.print("<Pump Activated #");
    Serial.println(well + 1);
    Serial.print(">\n");
    return well;
  }
  else {
    Serial.println("<\nArd. Invalid pump number.");
    Serial.print(">\n");
  }
  return -1;
}

void Deliver_Reward(int well) {
  TurnOnPump(well);
  Serial.println("<Delivering Reward");
  Serial.print(">\n");
}

void TurnOnPump(int well) {
  // set pump to on & set pump timer
  digitalWrite(Pumps_Pins[well], Pump_ON);
  Pump_State[well] = true;
  PumpTimeRef[well] = millis();
  PumpTimer[well] = 0;
}

// turn off pump and reset pump timers
void TurnOFFPump(int well) {
  digitalWrite(Pumps_Pins[well], Pump_OFF);
  Pump_State[well] = false;
  PumpTimeRef[well] = 15000UL;
  PumpTimer[well] = 0;
}

void ChangePumpOnDur() {
  int well = SerialReadNum();
  if (well >= 0 && well <= 5) {
    SetPumpDur(well);
  }
}

void SetPumpDur(int well) {
  unsigned long intimer = millis();
  bool startReading = false;
  bool finishedReading = false;
  char durbuffer[10];
  int  charcounter = 0;
  // read the duration as a string
  while (intimer >= (millis() - 5000) || finishedReading) {
    if (Serial.available()) {
      char bufferchar = Serial.read();
      if (startReading) {
        if (bufferchar == '>') {
          finishedReading = true;
          durbuffer[charcounter] = '\0';
          break;
        }
        else {
          if (bufferchar >= '0' && bufferchar <= '9') {
            durbuffer[charcounter] = bufferchar;
            charcounter++;
          }
          else if (bufferchar == 'x') { // reset
            finishedReading = true;
            Pump_ON_DUR[well] = Pump_ON_Default[well];
            Serial.print("Ard. Defaulting to original pump on duration:");
            Serial.println(Pump_ON_Default[well]);
            Serial.println("");
            Serial.println(">");
            return;
          }
          else {
            finishedReading = true;
            Serial.println("Ard. Invalid pump-on duration.");
            return;
          }
        }
      }
      if (bufferchar == '<') {
        Serial.println("Ard. Reading dur input. ");
        startReading = true;
      }
    }
  }
  if (finishedReading) {
    long dur = atol(durbuffer);
    if (dur >= 0 && dur <= 500) {
      Pump_ON_DUR[well] = dur;
      Serial.print("<Changed Pump-On Duration to:");
      Serial.println(dur);
      Serial.print(">\n");
    }
    else {
      Pump_ON_DUR[well] = Pump_ON_Default[well];
      Serial.print("<Input exceeds limits. Defaulting to original:");
      Serial.println(Pump_ON_Default[well]);
      Serial.print(">\n");
    }
  }
  else {
    Pump_ON_DUR[well] = Pump_ON_Default[well];
    Serial.println("<\nTimed out to input duration well");
    Serial.print(">\n");
  }
}
/****************************************
   Activate/Deactivate wells.
*****************************************/
int SelectWellToActive() {
  int well = SerialReadNum();
  if (well >= 0 && well <= 5) {
    ActivateWell(well);
    Serial.print("<Activated Well #");
    Serial.println(well + 1);
    Serial.print(">\n");
    return well;
  }
  else {
    Serial.println("<\nArd. Invalid well number.");
    Serial.print(">\n");
  }
  return -1;
}

int SelectWellToDeActive() {
  int well = SerialReadNum();
  if (well >= 0 && well <= 5) {
    DeActivateWell(well);
    Serial.print("<Deactivated Well #");
    Serial.println(well + 1);
    Serial.print(">\n");
    return well;
  }
  else {
    Serial.println("<\nArd. Invalid well number.");
    Serial.print(">\n");
  }
  return -1;
}

void ActivateWell(int well) {
  Well_Active_State[well] = true;

  if (well <= 1) {
    Well_LED_ON();
  };

  Well_Active_TimeRef[well] = millis();
  Well_Active_Timer[well] = 0;
  //Deliver_Reward(well);
  sendEventCode(AW, well + 1);
}

void DeActivateWell(int well) {
  Well_Active_State[well] = false;
  Well_Active_TimeRef[well] = 15000UL;
  Well_Active_Timer[well] = 0;
  Well_LED_OFF(well);
  sendEventCode(DW, well + 1);
}

void ActivateAllWells() {
  for (int well = 0; well < nWells; well++) {
    ActivateWell(well);
    //Deliver_Reward(well);
  }
}
void reset_states() {
  for (int ii = 0; ii < nWells; ii++) {
    DeActivateWell(ii);
    TurnOFFPump(ii);
  }
}

/****************************************
          Well LED functions
*****************************************/
void  Well_LED_ON() {
  // turn on LED on call for active wells only
  for (int well = 0; well < nWells; well++) {
    if (Well_Active_State[well]==true & Well_LED_State[well] == false) {
      digitalWrite(Well_LED_Pins[well], HIGH);
      Well_LED_State[well] = true;
    }
  }
}

void  Well_LED_OFF(int well) {
  digitalWrite(Well_LED_Pins[well], LOW);
  Well_LED_State[well] = false;
}

/****************************************
     Print Current States
*****************************************/
void print_states() {
  Serial.println("<State variables");
  for (int ii = 0; ii < nWells; ii++) {
    Serial.print("<States for well # ");
    Serial.println(ii + 1);
    Serial.print("<Well Active State = ");
    Serial.println(Well_Active_State[ii]);
    Serial.print("<Pump On Dur = ");
    Serial.println(Pump_ON_DUR[ii]);
  }
  Serial.println("<\n");
  Serial.println("<\n");
  if (ActiveCUE_ID >= 0) {
    Serial.print("Active Cue = ");
    Serial.println(ActiveCUE_ID + 1);
  }
  Serial.print(">\n");
}

