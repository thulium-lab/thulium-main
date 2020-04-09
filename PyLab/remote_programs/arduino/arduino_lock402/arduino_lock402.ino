// NOTES:
// Did not tested on real shutters
// It seams like arduino clock tikes not correctly, 12 ms in second slower than RIGOL. Introduced second_coefficient to equal them
// Serial input should end with '!' or '?', otherwise it is treated as bad. Command can be sent again
// Time delay of signal edge is <1ms and jitting <1ms
// NEW WAY of writing beam shutters: 'BS ' + shutters_channels '014' + ' ' + 't_val' where val is sum of all states with proper binary shift

#include "ctype.h"

const double second_coefficient = 1.014; // coeffitien reflects arduino time for 1s interval 0.988 - for second arduino
// variables
int i = 0;
int k = 0;
int j = 0;
// variables
char w[50];
String ws;
const byte n_words = 50; // maximum nuber of words in recieved messege
unsigned long t;
int words_number = 0; // number of words in last recieved command
String words[n_words]; // array of string to read from serial port to

int pwm_port=6;

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
  pinMode(pwm_port, OUTPUT); // configure output pwm pin
}

void loop() {
  // chech if smth has been sent in serial port and call handler
  if (Serial.available()){
    data_input_handler();
  }
}

// function that parses input commands
void data_input_handler() {
  //delay(1); // to all data come
  i = get_string_array(); // reads input and separates words
  if (i == -1){
    if (debug > 0 ){
    Serial.println("Bad");
    }
    return;
  }
//  Serial.println("Returned");
//  Serial.println(words[0]);
  
  if ( (words[0]).equals("*IDN") ) { // identification
    Serial.println("ArduinoUnoLock402");
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
  if ( (words[0]).equals("V") ) { // set state of wavelength meter shutters
        if( words_number != 2 ) { // check if input more or less correct
          if (debug > 0 ){
          Serial.println("Bad command");
          }
          return;
        }
       
      analogWrite(pwm_port, words[1].toFloat()*255/5);
    
    if (debug > 0 ){
      Serial.println("PWM write Ok");
    }
  }
}


int get_string_array()
{
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
if (debug == 10){
  Serial.print("Trying read");
    for (int i = 0; i < n_words; i++) {
      Serial.print(words[i]);
    }
    
      Serial.println("");
  
}
  if (i==0){
//    if (debug == 10) {
//      Serial.println(words[k]);
//    }
    return -1;
  }
  words_number = k+1;

//  Serial.println("Finished reading");
//  for(int i=0;i<words_number;i++)  {
//    // Printing throwght Serial Monitor
//    Serial.print(i);
//     Serial.println(words[i]);
//  }
  return 0;
//     Serial.println(words_number);
  //Serial.print("Input line ");
  //Serial.println(full);
}
