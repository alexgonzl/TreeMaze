unsigned long Well_Active_Timer[nWells];   // timer indicating how long LED has been on
unsigned long Well_IR_TimeRef[nWells];  // time reference: for IR detection
unsigned long Well_IR_Timer[nWells];    // timer for how long IR has been on.
unsigned long Well_IR_RefracTimeRef[nWells]; // timer for second detection

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
    Well_IR_RefracTimeRef[ii] = 0;

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
} // end setup

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
  if ((millis() - Well_IR_RefracTimeRef[well])>DETECT_REFRAC_THR) {       
    if (Well_Detect_State[well] == false) {
      if (Well_IR_State[well] == true) {
        
        Well_IR_Timer[well] = millis() - Well_IR_TimeRef[well];
        if (Well_IR_Timer[well] >= DETECT_TIME_THR) {
          Well_Detect_State[well] = true;
          ResetDetectTimer(well);
          Well_IR_RefracTimeRef[well] = millis();
          Serial.print("<Detection on Well # ");
          Serial.println(well + 1);
          Serial.print(">\n");
          sendEventCode(DD, well + 1);
        }
      }
    }
  }
}

// Reset IR Timer
void ResetDetectTimer(int well) {
  Well_IR_TimeRef[well] = 15000UL;
  Well_IR_Timer[well] = 0;
}
