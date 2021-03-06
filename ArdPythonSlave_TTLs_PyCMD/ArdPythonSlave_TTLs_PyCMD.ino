/* IR detectection using interrupt pins for the sensor shield setup.
    It sends an output the serial monitor and to the pumps.
    A well is active only if serial input allows it.

  Use of CmdMessenger for interfacing to PC.

  Alex Gonzalez
  Updated: 3/13/18
*/

// CUE library
#include <Adafruit_GFX.h>
#include <Adafruit_NeoMatrix.h>
#include <Adafruit_NeoPixel.h>
#include <CmdMessenger.h>
#ifdef __AVR__
#include <avr/power.h>
#endif

/*********************************
 Program constants
**********************************/
const long BAUD_RATE = 115200; // baud rate for serial communication. must match contro script
const long MAX_TIME_UL = 4294967295UL;
const long DETECT_TIME_THR  = 80; // in ms
const long DETECT_REFRAC_THR = 4000; // twenty seconds before registering a second detection
const bool Pump_ON = LOW; // LOW activates the pump
const bool Pump_OFF = HIGH; // HIGH deactivates the pump.
const int nWells = 6; // number of reward wells
const int nCues = 4; // max number of cues.
const int TTL_PulseDur = 10; // Output TTL Pulse Duration in ms
const int StateReportInterval = 5000; // send a report every 5 seconds
bool StateReportFlag = true;

// Default values for pump durations
const long Pump_ON_Default[nWells]   = {6, 6, 12, 12, 12, 12};
long Pump_ON_DUR[nWells]    = {6, 6, 12, 12, 12, 12};
long Pump_ON_DUR_Temp[nWells] = {6, 6, 12, 12, 12, 12};

/****************************
    Declaration of Arduino Pins
*******************************/
// PINs for CUE signals output and control.
const int CUEs1_PIN = 53;
// TTL Well LED Pins
const int TTL_LED_Pins[nWells] = {4, 5, 6, 7, 8, 9};
// TTL WELL IR Detect Pins
const int TTL_IR_Pins[nWells] = {10, 11, 12, 26, 27, 28};
// TTL CUE Code Pins
/*29->right. 30->left; 31 and 32 unused*/
const int TTL_CUE_Pins[nCues] = {29, 30, 31, 32};
// TTL Reward Delivered Pin (one pump activated)
const int TTL_RD_Pin = 33;
// Pins for the Pump outputs
const int Pumps_Pins[nWells] = {34, 35, 36, 37, 38, 39};
// Interrupt Pins for the input IR detects
const int Well_IR_Pins[nWells] = {2, 3, 21, 20, 19, 18};
// LED outout pins LEDs
const int Well_LED_Pins[nWells] = {40, 41, 42, 43, 44, 45};
// RPGIO IR detect outputs to RPI
const int RPGIO_IR_Detect[nWells] = {47,48,49,50,51,52};

/******************************************
        Setup of Neopixel Matrix
*******************************************/
Adafruit_NeoMatrix NeoPix = Adafruit_NeoMatrix(16, 16, CUEs1_PIN,
  NEO_MATRIX_TOP     + NEO_MATRIX_RIGHT +
  NEO_MATRIX_COLUMNS + NEO_MATRIX_PROGRESSIVE,
  NEO_GRB            + NEO_KHZ800);

const uint32_t  NP_blueviolet = NeoPix.Color(120, 0, 110);
const uint32_t  NP_green = NeoPix.Color(0, 120, 0);
const uint32_t  NP_white = NeoPix.Color(255, 255, 255);
const uint32_t  NP_off = NeoPix.Color(0, 0, 0);

/******************************************
        Cue parameters
*******************************************/
const uint32_t  CUE_Colors[3] = {NP_blueviolet, NP_green, NP_white}; // array for NP colors
const float CUE_Freqs[3] = {1.67, 3.85, 0};
// half cycles of CUE_Freqs in ms: HC = (1/F)/2*1000
const long CUE_HalfCycles[3] = {300, 130, 0};
const long CUE9_TimeLimit = 20;
// cue state variables
uint32_t  ActiveCueColor = NP_off;
float ActiveCUE_Freq = 0;
long ActiveCUE_HalfCycle = 0;
bool ActiveCUE_UP = false;
int ActiveCUE_ID = 0;
int TTL_CUE_ID = -1;
// Cue timers
unsigned long CUE_Timer;
unsigned long CUE_TimeRef;

/******************************************
        State variables
*******************************************/
// Serial State Variable:
bool SerialState = false;
// Well State Variables:
bool Well_IR_State[nWells]; // state variable for the wells IR interrupts
bool Well_Detect_State[nWells]; // state variable for wells IRs that passed threshold.
bool Well_LED_State[nWells]; // variable LED indicating on/off
bool Well_Active_State[nWells]; // state variable indicating active well
bool Pump_State[nWells]; // Pump: on/off
// TTL State Variables
bool TTL_IR_Detect_State[nWells]; // TTL PULSE indicating that there was a detection.

/******************************************
        Time references
*******************************************/
unsigned long Well_Active_TimeRef[nWells]; // time reference for LED on
unsigned long Well_Active_Timer[nWells];   // timer indicating how long LED has been on
unsigned long Well_IR_TimeRef[nWells];  // time reference: for IR detection
unsigned long Well_IR_Timer[nWells];    // timer for how long IR has been on.
unsigned long Well_IR_RefracTimeRef[nWells]; // timer for second detection
unsigned long TTL_IR_Detect_Timer[nWells]; // timer

unsigned long PumpTimeRef[nWells];      // time ref for pump on
unsigned long PumpTimer[nWells];        // timer for how long pump has been on

long StateReportTimer;

// Event codes
char RR[] = "RE"; // reward
char DD[] = "DE"; // detection
char AW[] = "AW"; // actived well
char AL[] = "AL"; // led on
char DL[] = "DL" ; // led offs
char DW[] = "DW"; // deactivated well (usually after detection)
char CA[] = "CA"; // cue on.
char CD[] = "CD"; // cue off/

/***************************************************
  CmdMessenger
****************************************************/
char field_separator   = ',';
char command_separator = ';';
char escape_separator  = '/';
CmdMessenger comm = CmdMessenger(Serial, field_separator, command_separator);

// List of Commands
enum
{
  kAcknowledge,       // 0, output: acknowledge
  kError,             // 1, output: error in processing
  kSendEvent,         // 2, output: send detecion events
  kStatus,            // 3, output: status output
  kStateVec,          // 4, output: send vector
  kActivateAllWells,  // 5, input
  kSelectWell_ACT,    // 6, input
  kSelectWell_DeACT,  // 7, input
  kToggleLED,         // 8, input
  kLED_ON,            // 9, input
  kLED_OFF,           // 10, input
  kSelectPump_ON,     // 11, input
  kChangePumpDur,     // 12, input
  kTurnPumpOnForXDur, // 13, input
  kSelectCUE_ON,      // 14, input
  kTurnCUE_OFF,       // 15, input
  kPrint_States,      // 16, input
  kStatusReq,         // 17, input`
  kReset_States,      // 18, input
};

void attachCommandCallbacks(){
  comm.attach(OnUnknownCommand);
  comm.attach(kActivateAllWells,ActivateAllWells);
  comm.attach(kSelectWell_ACT,SelectWell_ACT);
  comm.attach(kSelectWell_DeACT,SelectWell_DeACT);
  comm.attach(kToggleLED,ToggleLED);
  comm.attach(kLED_ON,LED_ON);
  comm.attach(kLED_OFF,LED_OFF);
  comm.attach(kSelectPump_ON,SelectPump_ON);
  comm.attach(kChangePumpDur,ChangePumpDur);
  comm.attach(kTurnPumpOnForXDur,TurnPumpOnForXDur);
  comm.attach(kSelectCUE_ON,SelectCUE_ON);
  comm.attach(kTurnCUE_OFF,TurnCUE_OFF);
  comm.attach(kPrint_States,Print_States);
  comm.attach(kStatusReq,StateVectorReport);
  comm.attach(kReset_States, Reset_States);
}

void OnUnknownCommand(){
   comm.sendCmd(kError,"Command without attached callback");
}

void SendEventCode(char* code, int num){
  char str[5];
  sprintf(str,"%s%d", code, num);
  comm.sendCmd(kSendEvent,str);
}

/***************************************************
  Setup
****************************************************/
void setup() {
  //  state variables for the wells & time references initiation
  for (int well = 0; well < nWells; well++) {

    Well_IR_State[well] = false;
    Well_Detect_State[well] = false;
    Well_LED_State[well] = false;
    Pump_State[well] = false;
    TTL_IR_Detect_State[well] = false;

    Well_Active_TimeRef[well] = MAX_TIME_UL;
    Well_IR_TimeRef[well] = MAX_TIME_UL;
    PumpTimeRef[well] = MAX_TIME_UL;
    Well_IR_RefracTimeRef[well] = 0;
    TTL_IR_Detect_Timer[well] = 0;

    Well_Active_Timer[well] = 0;
    PumpTimer[well] = 0;
    Well_IR_Timer[well] = 0;
  }

  // LEDs
  for (int well = 0; well < nWells; well++) {
    // set LED pins to outputs and to low
    pinMode(Well_LED_Pins[well], OUTPUT);
    digitalWrite(Well_LED_Pins[well], LOW);

    // RPGIO IR detect outputs
    pinMode(RPGIO_IR_Detect[well],OUTPUT);
    digitalWrite(RPGIO_IR_Detect[well], LOW);

    // IR inputs
    pinMode(Well_IR_Pins[well], INPUT_PULLUP);

    // Pump outputs
    pinMode(Pumps_Pins[well], OUTPUT);
    digitalWrite(Pumps_Pins[well], HIGH);

    // TTL LEDs Outputs
    pinMode(TTL_LED_Pins[well], OUTPUT);
    digitalWrite(TTL_LED_Pins[well],LOW);

    // TTL IR Detects
    pinMode(TTL_IR_Pins[well], OUTPUT);
    digitalWrite(TTL_IR_Pins[well],LOW);
  }

  // Cues
  for (int cue = 0; cue < nCues; cue++){
    pinMode(TTL_CUE_Pins[cue], OUTPUT);
    digitalWrite(TTL_CUE_Pins[cue],LOW);
  }

  // Reward Delivered
  pinMode(TTL_RD_Pin, OUTPUT);
  digitalWrite(TTL_RD_Pin,LOW);

  // Attach interrupts independently
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[0]), IR_Detect1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[1]), IR_Detect2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[2]), IR_Detect3, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[3]), IR_Detect4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[4]), IR_Detect5, CHANGE);
  attachInterrupt(digitalPinToInterrupt(Well_IR_Pins[5]), IR_Detect6, CHANGE);

  // Neopixel setup:
  NeoPix.begin();
  NeoPix.setBrightness(70);
  NeoPix.fillScreen(0);
  NeoPix.show();

  delay(500);
  Serial.begin(BAUD_RATE);
  attachCommandCallbacks();

  comm.sendCmd(kAcknowledge,"Arduino has started!");
  StateReportTimer = millis();
} // end setup

//Main
void loop() {
  if (Serial) {
    if (not SerialState) {
      SerialState = true;
    }
    // Check serial input.
    comm.feedinSerialData();
    /**************************************
      Process wells and timers.
    ***************************************/
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
        if (PumpTimer[well] >= Pump_ON_DUR_Temp[well]) {
          TurnOFFPump(well);
          SendEventCode(RR, well + 1);
          Pump_ON_DUR_Temp[well] = Pump_ON_DUR[well];
        }
      }
      // TTL IRs Timer reset
      if (TTL_IR_Detect_State[well] == true){
        if ( (millis()-TTL_IR_Detect_Timer[well])>=TTL_PulseDur ){
          TTL_IR_Detect_State[well] = false;
          TTL_IR_Detect_Timer[well] = MAX_TIME_UL;
          digitalWrite(TTL_IR_Pins[well],LOW);
        }
      }
    } // well loop

    /**************************************
      Process the CUE
    ***************************************/
    if (ActiveCUE_ID >= 1 & ActiveCUE_ID <= 4) {
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
    } else if (ActiveCUE_ID==9){
      CUE_Timer = millis() - CUE_TimeRef;
      if (CUE_Timer > CUE9_TimeLimit){
        ActiveCUE_ID = 0;
        ChangeCueColor(NP_off);
      }
    } //cue Processing
  } else if (SerialState) {
    SerialState = false;
    Reset_States();
    Serial.flush();
  }

  if (StateReportFlag==true){
    if ((millis()-StateReportTimer)>=StateReportInterval){
      StateReportTimer = millis();
      StateVectorReport();
      Serial.flush();
      }
  }
} // end of Main loop()

/**********************************************************
***********************************************************
***********************************************************
                    Dependent Routines
***********************************************************
***********************************************************
***********************************************************/

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

    TTL_IR_Detect_State[well] = false;
    TTL_IR_Detect_Timer[well] = MAX_TIME_UL;
    digitalWrite(TTL_IR_Pins[well],LOW);
  }
}

// Detection Threshold
void WellDetectThrCheck(int well) {
  if ((millis() - Well_IR_RefracTimeRef[well])>DETECT_REFRAC_THR) {
    if (Well_Detect_State[well] == false) {
      if (Well_IR_State[well] == true) {

        Well_IR_Timer[well] = millis() - Well_IR_TimeRef[well];
        // valid Detection
        if (Well_IR_Timer[well] >= DETECT_TIME_THR) {
          Well_Detect_State[well] = true;
          ResetDetectTimer(well);
          Well_IR_RefracTimeRef[well] = millis();
          SendEventCode(DD, well + 1);

          // send TTL for detection
          TTL_IR_Detect_State[well] = true;
          TTL_IR_Detect_Timer[well] = millis();
          digitalWrite(TTL_IR_Pins[well],HIGH);
        }
      }
    }
  }
}

// Reset IR Timer
void ResetDetectTimer(int well) {
  Well_IR_TimeRef[well] = MAX_TIME_UL;
  Well_IR_Timer[well] = 0;
}

/****************************************
              Cue Control
*****************************************/
void SelectCUE_ON() {
  //int cue = comm.readInt16Arg();
  int cue = comm.readBinArg<int>();
  if (cue >= 1 && cue <= 9) {
    ActiveCUE_ID = cue;
    SendEventCode(CA, cue);
  }
  else {
    ActiveCUE_ID = 0;
    comm.sendCmd(kError, "Invalid Cue.");
  }
  SetCueParams(ActiveCUE_ID);
}

void TurnCUE_OFF() {
  SetCueParams(0);
  CUE_TimeRef = MAX_TIME_UL;
  CUE_Timer   = 0;
  SendEventCode(CD, ActiveCUE_ID);
}

void SetCueParams(int CueNum) {
  switch (CueNum) {
    // color 1
    case 1: // violet low freq -> right
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[0];
      ActiveCUE_HalfCycle = CUE_HalfCycles[0];
      TTL_CUE_ID = 0;
      break;
    case 2: // violet high freq right
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[1];
      ActiveCUE_HalfCycle = CUE_HalfCycles[1];
      TTL_CUE_ID = 0;
      break;
    // color 2
    case 3: // green low freq left
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[0];
      ActiveCUE_HalfCycle = CUE_HalfCycles[0];
      TTL_CUE_ID = 1;
      break;
    case 4: // green high freq left
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[1];
      ActiveCUE_HalfCycle = CUE_HalfCycles[1];
      TTL_CUE_ID = 1;
      break;
    // constant colors
    case 5: // violet right
      ActiveCueColor = CUE_Colors[0];
      ActiveCUE_Freq = CUE_Freqs[2];
      ActiveCUE_HalfCycle = CUE_HalfCycles[2];
      TTL_CUE_ID = 0;
      break;
    case 6: // green left
      ActiveCueColor = CUE_Colors[1];
      ActiveCUE_Freq = CUE_Freqs[2];
      ActiveCUE_HalfCycle = CUE_HalfCycles[2];
      TTL_CUE_ID = 1;
      break;
    case 9: // white
      ActiveCueColor = NP_white;
      ActiveCUE_Freq = CUE_Freqs[2];
      ActiveCUE_HalfCycle = CUE_HalfCycles[2];
      TTL_CUE_ID = 2;
      break;
    default:
      ActiveCUE_ID = 0;
      ActiveCueColor = NP_off;
      ActiveCUE_Freq = 0;
      ActiveCUE_HalfCycle = 0;
      TTL_CUE_ID = -1;
      break;
  }
  ChangeCueColor(ActiveCueColor);
  if (TTL_CUE_ID>=0) {
    digitalWrite(TTL_CUE_Pins[TTL_CUE_ID],HIGH);
  }
}

void ChangeCueColor(uint32_t col) {
  if (col == NP_off) {
    NeoPix.fillScreen(0);
    for (int cue = 0; cue < nCues; cue++){
      digitalWrite(TTL_CUE_Pins[cue],LOW);
    }
  } else {
    NeoPix.fillScreen(col);
  }
  NeoPix.show();
  CUE_TimeRef = millis();
  CUE_Timer   = 0;
}

/****************************************
      Pump/Reward Control
*****************************************/
void SelectPump_ON() {
  int wella = comm.readBinArg<int>();
  int wellb = comm.readBinArg<int>();
  int wellc = comm.readBinArg<int>();

  int well = findMode3(wella,wellb,wellc);
  
  if (well >= 0 && well <= 5) {
    TurnOnPump(well);
    //comm.sendCmd(kAcknowledge, "Pump On");
  } else {
    comm.sendCmd(kError, "Invalid Well.");
  }
}

void Deliver_Reward(int well) {
  TurnOnPump(well);
}

void TurnOnPump(int well) {
  // set pump to on & set pump timer
  digitalWrite(Pumps_Pins[well], Pump_ON);
  digitalWrite(TTL_RD_Pin,HIGH);
  Pump_State[well] = true;
  PumpTimeRef[well] = millis();
  PumpTimer[well] = 0;
}

// turn off pump and reset pump timers
void TurnOFFPump(int well) {
  digitalWrite(Pumps_Pins[well], Pump_OFF);
  digitalWrite(TTL_RD_Pin,LOW);
  Pump_State[well] = false;
  PumpTimeRef[well] = MAX_TIME_UL;
  PumpTimer[well] = 0;
}

void ChangePumpDur() {
  int well = comm.readBinArg<int>();
  int dur = comm.readBinArg<int>();
  if (well >= 0 && well <= 5) {
    SetPumpDur(well,dur);
  }
}

void TurnPumpOnForXDur(){
  //int well = comm.readInt16Arg();
  //int dur = comm.readInt16Arg();
  int well = comm.readBinArg<int>();
  int dur = comm.readBinArg<int>();
  if (well >= 0 && well <= 5) {
    if (dur>0 && dur<=250){
      Pump_ON_DUR_Temp[well] = dur;
      //comm.sendCmd(kAcknowledge,"Delivering specified reward.");
      Deliver_Reward(well);
    } else {
      comm.sendCmd(kError,"Invalid Pump Duration.");
    }
    } else {
    comm.sendCmd(kError, "Invalid Well.");
  }
}

void SetPumpDur(int well, int dur) {
  if (dur>0 && dur <=250){
    Pump_ON_DUR[well] = dur;
    Pump_ON_DUR_Temp[well] = dur;
    char str[30];
    sprintf(str, "Changed Pump %d to dur= %d.",well +1,dur);
    comm.sendCmd(kStatus,str);
  } else {
    Pump_ON_DUR[well] = Pump_ON_Default[well];
    comm.sendCmd(kError, "Invalid Pump Duration");
  }
}

/****************************************
   Activate/Deactivate wells.
*****************************************/
void SelectWell_ACT() {
  //int well = comm.readInt16Arg();
  int wella = comm.readBinArg<int>();
  int wellb = comm.readBinArg<int>();
  int wellc = comm.readBinArg<int>();

  int well = findMode3(wella,wellb,wellc);
  
  if (well >= 0 && well <= 5) {
    ActivateWell(well);
    //comm.sendCmd(kAcknowledge, "Activated Well");
  } else {
    comm.sendCmd(kError,"Invalid Well.");
  }
}

void SelectWell_DeACT() {
  //int well = comm.readInt16Arg();
  int wella = comm.readBinArg<int>();
  int wellb = comm.readBinArg<int>();
  int wellc = comm.readBinArg<int>();

  int well = findMode3(wella,wellb,wellc);
  
  if (well >= 0 && well <= 5) {
    DeActivateWell(well);
    //comm.sendCmd(kAcknowledge,"Deactivated Well");
  } else{
    comm.sendCmd(kError,"Invalid Well.");
  }
}

void ActivateWell(int well) {
  if (Well_Active_State[well]==false){
    Well_Active_State[well] = true;
    Well_Active_TimeRef[well] = millis();
    Well_Active_Timer[well] = 0;
  
    Well_IR_State[well] = false;
    Well_Detect_State[well] = false;
    digitalWrite(TTL_IR_Pins[well],LOW);
  
    Well_IR_RefracTimeRef[well] = 0;
    ResetDetectTimer(well);
  
    SendEventCode(AW, well + 1);
  }
}
void DeActivateWell(int well) {
  if (Well_Active_State[well]==true){
    Well_Active_State[well] = false;
    Well_Active_TimeRef[well] = MAX_TIME_UL;
    Well_Active_Timer[well] = 0;
    Well_LED_OFF(well);
    SendEventCode(DW, well + 1);
  }
}

void ActivateAllWells() {
  for (int well = 0; well < nWells; well++) {
    Well_LED_ON(well);
    ActivateWell(well);
  }
  //comm.sendCmd(kAcknowledge, "All Wells Activated.");
}

void Reset_States() {
  for (int well = 0; well < nWells; well++) {
    DeActivateWell(well);
    TurnOFFPump(well);
  }
  TurnCUE_OFF();
}

/****************************************
          Well LED functions
*****************************************/
void LED_ON(){
  //int well = comm.readInt16Arg();
  int wella = comm.readBinArg<int>();
  int wellb = comm.readBinArg<int>();
  int wellc = comm.readBinArg<int>();

  int well = findMode3(wella,wellb,wellc);
  
  if (well >=0 && well <= 5){
    Well_LED_ON(well);
    //comm.sendCmd(kAcknowledge, "LED ON");
  } else{
    comm.sendCmd(kError,"Invalid Well");
  }
}
void LED_OFF(){
  //int well = comm.readInt16Arg();
  int wella = comm.readBinArg<int>();
  int wellb = comm.readBinArg<int>();
  int wellc = comm.readBinArg<int>();

  int well = findMode3(wella,wellb,wellc);
  
  if (well >=0 && well <= 5){
    Well_LED_OFF(well);
    //comm.sendCmd(kAcknowledge,"LED OFF");
  } else{
    comm.sendCmd(kError,"Invalid Well");
  }
  SendEventCode(DL, well + 1);
}

void  Well_LED_ON(int well) {
  if (Well_LED_State[well] == false){
    digitalWrite(Well_LED_Pins[well], HIGH);
    digitalWrite(TTL_LED_Pins[well], HIGH);
    Well_LED_State[well] = true;
    SendEventCode(AL, well + 1);
  }
}

void  Well_LED_OFF(int well) {
  if (Well_LED_State[well] == true) {
    digitalWrite(Well_LED_Pins[well], LOW);
    digitalWrite(TTL_LED_Pins[well], LOW);
    Well_LED_State[well] = false;
    SendEventCode(DL, well + 1);
  }
}

void ToggleLED(){
  //int well = comm.readInt16Arg();
  int well = comm.readBinArg<int>();
  if (well >= 0 && well <= 5){
    if (Well_LED_State[well] == false){
      Well_LED_ON(well);
    }  else {
      Well_LED_OFF(well);
    }
    //comm.sendCmd(kAcknowledge,"LED_Toggle");
  } else {
    comm.sendCmd(kError,"Invalid Well");
  }
}

/****************************************
     Print Current States
*****************************************/
void Print_States() {
  comm.sendCmd(kStatus,"State LED and Pump Dur for each well:");
  for (int well = 0; well < nWells; well++) {
    char str1[40];
    sprintf(str1,"%d: State=%d LED=%d PumpDur=%d", well + 1, Well_Active_State[well], Well_LED_State[well], Pump_ON_DUR[well]);
    comm.sendCmd(kStatus,str1);
  }
  char str2[20];
  sprintf(str2,"Active Cue = %d", ActiveCUE_ID);
  comm.sendCmd(kStatus,str2);
  Serial.flush();
}

void StateVectorReport(){
  char temp[15];
  for (int well = 0; well<nWells; well++){
    sprintf(temp,"%d-%d-%d-%d",well,Well_Active_State[well], Well_LED_State[well], Pump_ON_DUR[well]);
    comm.sendCmd(kStateVec,temp);
  }
}

int findMode3(int a, int b, int c){
  int a_count = 1;
  int b_count = 1;
  int c_count = 1;

  if (a==b){
    a_count+=1;
    b_count+=1;
  }
  if (b==c){
    b_count+=1;
    c_count+=1;
  }
  if (c==a){
    a_count+=1;
    c_count+=1;
  }
  
  if (a_count>=b_count and a_count>=c_count){
    return a;
    }
  else if (b_count>=a_count and b_count>=c_count){
    return b;
    }
  else if (c_count>=a_count and c_count>=b_count){
    return c;
    }
  else {
    return a;
  }
}

