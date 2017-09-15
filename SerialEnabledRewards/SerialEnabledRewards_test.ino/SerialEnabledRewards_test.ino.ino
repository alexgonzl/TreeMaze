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

  Alex Gonzalez
  Updated: 9/12/17
*/

const long BAUD_RATE = 115200; // baud rate for serial communication. must match contro script
const long DETECT_TIME_THR  = 500; // in ms
const bool Pump_ON = LOW; // LOW activates the pump
const bool Pump_OFF = HIGH; // HIGH deactivates the pump.
const int nWells = 6; // number of reward wells

/*  ***************************
    Declaration of Arduino Pins
*/
// PINs for CUE signals output and control.
const int CUEs1 = 16;
const int CUEs2 = 17;

// TTL Well LED Pins
const int TTL_LED_Pins[6] = {4, 5, 6, 7, 8, 9};

// TTL WELL IR Detect Pins
const int TTL_IR_Pins[6] = {10, 11, 12, 26, 27, 28};

// TTL CUE Code Pins
const int TTL_CUE_Pins[4] = {29, 30, 31, 32};

// TTL Reward Delivered Pin (one pump activated)
const int TTL_RD_Pin = 33;

// Pins for the Pump outputs
//const int Pumps_Pins[6] = {34, 35, 36, 37, 38, 39};
const int Pumps_Pins[6] = {34, 35, 36, 37, 38, 39};


// Interrupt Pins for the input IR detects
const int Well_IR_Pins[6] = {2, 3, 21, 20, 19, 18};

// LED outout pins LEDs
const int Well_LED_Pins[6] = {40, 41, 42, 43, 44, 45};

// Default values for pump durations
const long Pump_ON_Default[6]   = {20, 20, 30, 30, 30, 30};
long Pump_ON_DUR[6]    = {20, 20, 30, 30, 30, 30};
// in ms (100ms=0.25ml; 40ms=0.1ml)
/* **********************************
   End of Declaration of Arduino Pins
*/

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

char RR[] = "RR";
char DD[] = "DD";
char AW[] = "AW";
char DW[] = "DW";

// Setup
void setup() {
  //  state variables & time references initiation
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

  // J LEDs
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

  delay(500);
  Serial.begin(BAUD_RATE);
  Serial.println("<");
  Serial.println("<Initiation complete. Waiting for a detection.");
  Serial.print(">");
}

//Main
void loop() {

  // check for which well to activate
  ProcessInput();
  for (int well = 0; well < nWells; well++) {
    WellDetectThrCheck(well);
    // if well is active, check to deliver reward
    if  (Well_Active_State[well] == true) {
      if (Pump_State[well] == false && Well_Detect_State[well] == true) {
        Deliver_Reward(well);
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
        if  (Well_Active_State[well] == true) {
          DeActivateWell(well);
        }
      }
    }
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

// send event code
void sendEventCode(char* code, int num) {
  char str[10];
  sprintf(str, "<EC_%s%d", code, num);
  Serial.println(str);
  Serial.println(">\n");
}

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

// Reset IR Timer.s
void ResetDetectTimer(int well) {
  Well_IR_TimeRef[well] = 15000UL;
  Well_IR_Timer[well] = 0;
}

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
      default:
        Serial.println("<IncorrectSuffix");
        Serial.print(">\n");
        break;
    }
  }
}

// Read which well
int SerialReadPump() {
  unsigned long intimer = millis();
  while (intimer >= (millis() - 5000)) {
    if (Serial.available()) {
      int well = Serial.read();
      well = well - 49;
      if (well >= 0 && well <= 5) {
        return well;
      }
      else {
        Serial.print("<Input not allowed.");
        Serial.println(well);
        Serial.print(">\n");
        return -1;
        }
    }
  }
  Serial.println("<\nTimed out to select well");
  Serial.print(">\n");
  return -1;
}


// Read selected well duration
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
          else if (bufferchar == 'x'){ // reset
            finishedReading = true;
            Pump_ON_DUR[well] = Pump_ON_Default[well];
            Serial.print("Ard. Defaulting to original pump on duration:");
            Serial.println(Pump_ON_Default[well]);
            Serial.println("");
            Serial.println(">");
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
    Serial.println("input as a string");
    Serial.println(durbuffer);
    long dur = atol(durbuffer);
    //long =
    Serial.println("input as an int");
    Serial.println(dur);

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

int SelectWellToActive() {
  int well = SerialReadPump();
  if (well >= 0 && well <= 5) {
    ActivateWell(well);
    Serial.print("<Activated Well #");
    Serial.println(well + 1);
    Serial.print(">\n");
  }
  return well;
}

int SelectWellToDeActive() {
  int well = SerialReadPump();
  if (well >= 0 && well <= 5) {
    DeActivateWell(well);
    Serial.print("<Deactivated Well #");
    Serial.println(well + 1);
    Serial.print(">\n");
  }
  return well;
}

int SelectPumpToTurnOn() {
  int well = SerialReadPump();
  if (well >= 0 && well <= 5) {
    TurnOnPump(well);
    Serial.print("<Pump Activated #");
    Serial.println(well + 1);
    Serial.print(">\n");
  }
  return well;
}

void ChangePumpOnDur() {
  int well = SerialReadPump();
  if (well >= 0 && well <= 5) {
    SetPumpDur(well);
  }
}

// After detection threshold.
// Deliver Reward (activate pump) and reset IR timer/state
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

void ActivateWell(int well) {
  Well_Active_State[well] = true;
  Well_Active_TimeRef[well] = millis();
  Well_Active_Timer[well] = 0;
  Well_LED_ON(well);
  sendEventCode(AW, well + 1);
}

void  ActivateAllWells() {
  for (int ii = 0; ii < nWells; ii++) {
    ActivateWell(ii);
  }
}

void DeActivateWell(int well) {
  Well_Active_State[well] = false;
  Well_Active_TimeRef[well] = 15000UL;
  Well_Active_Timer[well] = 0;
  Well_LED_OFF(well);
  sendEventCode(DW, well + 1);
}

void  Well_LED_ON(int well) {
  // set LED timers and set LED state to ON
  digitalWrite(Well_LED_Pins[well], HIGH);
  Well_LED_State[well] = true;
}

void  Well_LED_OFF(int well) {
  digitalWrite(Well_LED_Pins[well], LOW);
  Well_LED_State[well] = false;
}

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
  Serial.print(">\n");
}

void reset_states() {
  for (int ii = 0; ii < nWells; ii++) {
    DeActivateWell(ii);
    TurnOFFPump(ii);
  }
}
