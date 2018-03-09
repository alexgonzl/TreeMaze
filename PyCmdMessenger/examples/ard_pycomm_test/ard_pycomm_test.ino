#include "CmdMessenger.h"  // CmdMessenger

char field_separator   = ',';
char command_separator = ';';
char escape_separator  = '/';

CmdMessenger c = CmdMessenger(Serial, field_separator, command_separator);
//const int BAUD_RATE = 9600;
//const int BAUD_RATE = 19200;
//const int BAUD_RATE = 28800;
//const int BAUD_RATE = 38400;
//const int BAUD_RATE = 74880;
//const int BAUD_RATE = 115200;
#define BAUD_RATE 115200
//
//enum {
//  ack,
//  hello,
//  sum_two_ints,
//  sum_is,
//  msg,
//  unknown,
//  err,
//};
//void on_sum_two_ints(){
//  int value1 = c.readBinArg<int16_t>();
//  int value2 = c.readBinArg<int16_t>();
//  c.sendBinCmd(sum_is,value1+value2);
//}

//void long_message(){
//  c.sendCmdStart(msg);
//  c.sendCmdArg("oh hello there");
//  c.sendCmdArg("yup still here.");
//  c.sendCmdEnd();
//}
//void attach_callbacks(){
//  c.attach(hello,on_hello);
//  c.attach(sum_two_ints,on_sum_two_ints);
//  c.attach(msg, long_message);
//  c.attach(unknown,on_unknown);
//}
enum {
  ack, //0
  hello, // 1
  sum2i, // 2
  sum2i_r, // 3
  err, // 4
};
void on_unknown(){
  c.sendCmd(err,"Unknown Command.");
}
void on_sum2i(){
  int v1 = c.readInt16Arg();
  int v2 = c.readInt16Arg();
  c.sendCmd(sum2i_r,v1+v2);
//  int v1 = c.readBinArg<int>();
//  Serial.println(v1);
//  int v2 = c.readBinArg<int>();
//  Serial.println(v2);
//  Serial.println(v1+v2);
//  c.sendBinCmd(sum2i_r,v1+v2);
}
void on_hello(void) {
  c.sendCmd(ack, "oh hello!!!!!!!!!!!!!!");
}
void attach_callbacks(void) {
  c.attach(hello, on_hello);
  c.attach(sum2i, on_sum2i); 
  c.attach(on_unknown);
}
void setup() {
  Serial.begin(BAUD_RATE);
  attach_callbacks();
}
void loop() {
  c.feedinSerialData();
}
