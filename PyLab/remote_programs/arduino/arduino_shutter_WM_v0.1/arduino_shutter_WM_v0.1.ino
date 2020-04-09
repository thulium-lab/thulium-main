// Developed by Artem Golovizin, LPI (FIAN). Based on arduino_shutters_v2.2., 
// Controlls shutters based on simple stepper motors in a logic way: 0 - only bias coil is on, 1 - both coils are on.
// Tipical resistences are 50-200 Ohm, the larger difference between bias and TTL resistence the larger rotation, tipical 10 degrees.

// Commands look like 'WMShutters c_i s_i c_j s_j!' where c_i,j - is a channel number (0 - on the main board), s_i,j - is a channel state, '!' in the end of line indicates command end.

#include "ctype.h"

const double second_coefficient = 1.014; // coeffitien reflects arduino time for 1s interval 0.988 - for second arduino
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
// 0 for no unnesessery data to serial, 1 - for the most needed, 2 - for debugging pulse_scheme, 3 - for debugging WavelenghtMeter, 10 - for all 
int debug=1; 
  int counter = 0;
int input_size;
String full, tail;
char b;
int first_space;
String msg;
String channel_string;

void setup() {
  Serial.begin(9600); // boud rate 
//  attachInterrupt(0,interrupt_handler,RISING); // connect trigger on pin 2 to interrupt with handler function interrupt_handler, edge is rising
  for (i = 0; i < ports_number; i++) {
    pinMode(available_ports[i], OUTPUT); // configure output shutter pins
  }
}

// interrupt (trigger) handler; rises flag 'interrupted' to then stat SMTH (i.e. writing to beam shutter channels)
//void interrupt_handler(){
//  t = millis();
//  msg = "interrupt t=" + String(t);
//  if (t - last_trigger_time > 10){ // it is not a noise  -- somewhy this part is needed
//    last_time = t; // write down time when trigger arrived (sequence is started)
//    last_trigger_time = t;
//    current_edge = 0;
//    interrupted=true; // rise flag
//    msg += "   good";
//  }
//  else {
//    msg += "   bad";
//  }
//  if (debug == 2 or debug == 10){
//    Serial.println(msg);
//  }
//  if (debug == 1){
//    Serial.print("i");
//  }
//}

void loop() {
//  if (interrupted){ // if interruption occured (trigger came) this flag is rised 
//    interrupted=false; // clear flag
//    DO SMTH
//  }
  // chech if smth has been sent in serial port and call handler
  if (Serial.available()){
    data_input_handler();
  }
}

// function that parses input commands
void data_input_handler() {
  i = get_string_array(); // reads input and separates words
  if (i == -1){
    if (debug > 0 ){
    Serial.println("Bad");
    }
    return;
  }
  handled = false; // dedicated
  
  if ( (words[0]).equals("*IDN") ) { // identification
    Serial.println("WMArduinoUnoShutters");
  }
  if ( (words[0]).equals("debug") ) { // set debug mode
    if  (words_number == 2){
    debug = words[1].toInt();
    Serial.println("Debug state updated");
    }
    else {
      Serial.println("incorrect command");
    }
  }
  if ( (words[0]).equals("WMShutters") ) { // set state of wavelength meter shutters
        if( (words_number-1)%2 ) { // check if input more or less correct
          if (debug > 0 ){
          Serial.println("Bad WMShutters command");
          }
          return;
        }
    for (int i = 1; i < words_number; i+=2)
    {
      if (debug ==3 or debug==10 ){
      Serial.print(words[i].toInt());
      Serial.print("   ");
      Serial.println(words[i+1].toInt());
      }
      digitalWrite(available_ports[words[i].toInt()], words[i+1].toInt());
    }
    if (debug == 2 ){
      Serial.println("WS Ok");
    }
    if (debug == 1 ){
      Serial.print(".");
    }
  }
}


int get_string_array()
{
//  detachInterrupt(0); // it was an idea that some problems are due to the interrupt, but they are not
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
if (debug == 10){
  Serial.print("Trying read");
    for (int i = 0; i < n_words; i++) {
      Serial.print(words[i]);
    }
    
      Serial.println("");
  
}
  words_number = k+1;
//  attachInterrupt(0,interrupt_handler,RISING);
  return 0;
}
