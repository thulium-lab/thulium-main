// NOTES:
// Did not tested on real shutters
// It seams like arduino clock tikes not correctly, 12 ms in second slower than RIGOL. Introduced second_coefficient to equal them
// Serial input should end with '!' or '?', otherwise it is treated as bad. Command can be sent again
// Time delay of signal edge is <1ms and jitting <1ms

#include "ctype.h"

const double second_coefficient = 1;//1194.0/1200; //0.988; // coeffitien reflects arduino time for 1s interval 
int available_ports[] = {A0, 12, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, A1, A2, A3, A4, A5};
const int ports_number = 17;
const int trig_pin = 2; // pin for triggering arduino on start of time sequence
// variables
int i = 0;
int k = 0;
int j = 0;
int int_arr[34]; // int array for handling channel:state for each beam shutter at specific time edge 
int int_arr_current_length = 0; // current length of channels and states for beam shutters which are to write
// variables
char w[50];
String ws;
const byte n_words = 50; // maximum nuber of words in recieved messege
unsigned long last_time = 10; // last time when edge (beam shutters states) was changed
unsigned long last_trigger_time = 0; // last time when triggered
unsigned long t;
int words_number = 0; // number of words in last recieved command
int n_sequences; // number of sequencies t_ch1_s1_ch2_s2..._ where at time t channels' states chi changes ti si 
String words[n_words]; // array of string to read from serial port to
String edge_sequence[n_words]; // array of strings to save sequences of beam shutters
int edge_delay=0; // delay of next edge (where any beam shutter state changes) from previous one in ms
int current_edge=0; // serial number of currently set edge (state)

bool handled ; // artifact from previous version (not used now); if serial input command is handled
bool interrupted = false; // if interruption from trigger occured this flag rises, when interruption is handled it crears
bool sequence_finished=false; // rises when beam shutter sequence is finished, after that programm waits when next trigger comes

  int counter = 0;
int input_size;
String full, tail;
char b;
int first_space;
  
void setup() {
  Serial.begin(57600); // boud rate 
  attachInterrupt(0,interrupt_handler,RISING); // connect trigger on pin 2 to interrupt with handler function interrupt_handler, edge is rising
  for (i = 0; i < ports_number; i++) {
    pinMode(available_ports[i], OUTPUT); // configure output shutter pins
  }
}

// interrupt (trigger) handler; rises flag 'interrupted' to then stat writing to beam shutter channels
void interrupt_handler(){
  Serial.print("interrupted t=");
  t = millis();
  Serial.print(t);
  if (t - last_trigger_time > 2){ // it is not a noise
    last_time = t; // write down time when trigger arrived (sequence is started)
    last_trigger_time = t;
    current_edge = 0;
    interrupted=true; // rise flag
    Serial.println("   good");
  }
  else {
    Serial.println("   bad");
  }
  
}
void loop() {
  // if interruption occured (trigger came) this flag is rised 
  if (interrupted){
    interrupted=false; // clear flag
    sequence_finished = false; // clear flag
    edge_delay = 0; // null previous edge delay; first sequence ALWAYS should start at relative time t=0
    write_channels(); // call routine
  }
  // if sequence is not yet finished and it is less than 2ms befor next edge shold be written
  if (not sequence_finished and millis()-last_time > edge_delay-1){
    while (millis()-last_time > edge_delay){ 
      // spinning here; this is done to not be desturebed by serial input
    }
    // when we leave previous cicle call routine
    write_channels();
  }
  // chech if smth has been sent in serial port and call handler
  if (Serial.available()){
    data_input_handler();
  }
}

// writing beam shutter states 
void write_channels(){
//  Serial.print(millis());
//  Serial.print("; current_edge ");
//  Serial.print(current_edge);
  j=0;
  k=0;
  ws = edge_sequence[current_edge]; // read current state as string
//  Serial.println(ws);
  for (int i=0; i<ws.length();i++){
    if (ws[i]=='_' and j==0){ // pass first digit as it is time mark
      j=i;
      continue;
    }
    else if (ws[i]=='_'){
      int_arr[k] = ws.substring(j+1,i).toInt(); // save each number which is ither channel_number or state
//      Serial.println(int_arr[k]);
      k++;
      j=i;
    }
  }
  int_arr_current_length = k; // save length of channel_number or state array for current sequence
//  Serial.print("Start writing time ");
//  Serial.println(micros());
  for (int i=0;i<int_arr_current_length;i+=2){
    Serial.print(int_arr[i]);
    Serial.print(" state ");
    Serial.println(int_arr[i+1]);
    digitalWrite(available_ports[int_arr[i]], int_arr[i+1]); // write state to beam shutter output pin
  }
//  Serial.print("End writing time ");
  // if this is the last edge of beam shutters 
  if (current_edge == n_sequences - 1){
    sequence_finished = true; // rise this flag
 //   Serial.println("Last sequence is finished");
  }
  else {// if not last
//    Serial.println(millis());
//    Serial.println(current_edge);
    ws = edge_sequence[current_edge+1]; //new string of beam shutters state
//    Serial.println(ws);
  for (int i=0; i<ws.length();i++){
    if (ws[i]=='_'){ // find first _, thus identifying edge time, calculating delay
//      Serial.println(
//      edge_delay = int(ws.substring(0,i).toInt()/second_coeffitient) - edge_delay;
//      edge_delay = ws.substring(0,i).toInt() - edge_delay;
      last_time = last_time + int(ws.substring(0,i).toInt()/second_coefficient) - edge_delay;
      edge_delay = int(ws.substring(0,i).toInt()/second_coefficient);
//      Serial.print("New delay ");
  //    Serial.println(edge_delay);
      break;
    }
    }
    current_edge = current_edge + 1; // update
  }
}

// function that parses input commands
void data_input_handler() {
  //delay(1); // to all data come
  i = get_string_array(); // reads input and separates words
  if (i == -1){
    Serial.println("Bad");
    return;
  }
  handled = false; // dedicated
//  Serial.println("Returned");
//  Serial.println(words[0]);
  
  if ( (words[0]).equals("*IDN") ) { // identification
    Serial.println("ArduinoUnoShutters");
  }

  if ( (words[0]).equals("WMShutters") ) { // set state of wavelength meter shutters
        if( (words_number-1)%2 ) { // check if input more or less correct
          Serial.println("-1");
          return;
        }
    for (int i = 1; i < words_number; i+=2)
    {
//      Serial.print(words[i].toInt());
//      Serial.print("   ");
//      Serial.println(words[i+1].toInt());
      digitalWrite(available_ports[words[i].toInt()], words[i+1].toInt());
    }
      Serial.println("Ok");
  }
 if ( (words[0]).equals("BeamShutters") ) { // saves all sequences to edge_sequence array of string
  //  test command BeamShutters 0_1_0_2_0_3_0_4_0_5_0_ 300_1_0_2_0_3_0_4_0_5_0_ 1000_1_1_2_1_3_1_4_1_5_1_
  // BeamShutters 0_1_0_2_0_3_0_4_0_5_0_ 300_1_0_2_0_3_0_4_0_5_0_ 400_1_0_2_0_3_0_4_0_5_0_ 500_1_0_2_0_3_0_4_0_5_0_ 600_1_0_2_0_3_0_4_0_5_0_ 1000_1_1_2_1_3_1_4_1_5_1_
  // BeamShutters 0_1_0_2_0_3_0_4_0_5_0_ 300_1_0_2_0_3_0_4_0_5_0_ 400_1_1_2_1_3_1_4_1_5_1_ 500_1_0_2_0_3_0_4_0_5_0_ 600_1_0_2_0_3_0_4_0_5_0_ 1000_1_1_2_1_3_1_4_1_5_1_!
    for (int i = 0; i < n_words; i++) {
      edge_sequence[i] = "";
    }
  n_sequences = words_number-1; // number of edges

//  Serial.println(words_number);
  for (int i = 1; i < words_number; i++){ // writing
//     Serial.print(i-1);
//     Serial.println(words[i]);
     edge_sequence[i-1] = words[i];
    }     
   for (int i = 0; i < n_sequences; i++){  
//    Serial.print(i);     
//    Serial.println(edge_sequence[i]);
    }
      Serial.println("Ok");
 }
}


int get_string_array()
{
//  detachInterrupt(0); // it was an idea that some problems are due to the interrupt, but they are not

//  Serial.println("getting string");
//  Serial.flush();
//  delay(1);              // Wait for getting all data
  // it is nessesery to set strings to "", otherwise smth doesn't work
  full = "";
  for (int i = 0; i < n_words; i++) {
      words[i] = "";
    }
  k=0;
  i=30000; // numbers to try read serial input
  while (i>0){
    b=char(Serial.read());
    if (b == '!' or b=='?'){
      break;
    }
    else if (b ==' '){
      k++;
    }
    else if (b>=0){
      words[k]+=b;
    }
    i--;
  }
//  Serial.println(i);
  if (i==0){
//    Serial.println("Wrong reading");
    return -1;
  }
  words_number = k+1;

//  Serial.println("Finished reading");
//  for(int i=0;i<words_number;i++)  {
//    // Printing throwght Serial Monitor
//    Serial.print(i);
//     Serial.println(words[i]);
//  }
//  attachInterrupt(0,interrupt_handler,RISING);
  return 0;
//     Serial.println(words_number);
  //Serial.print("Input line ");
  //Serial.println(full);
}
