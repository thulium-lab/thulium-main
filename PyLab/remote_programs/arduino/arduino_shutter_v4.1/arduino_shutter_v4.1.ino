#include <SPI.h>
#include <EEPROM.h>  
#include <avr/io.h>
#include <avr/interrupt.h>


int debug = 1;
bool first_run = true;

const double second_coefficient = 1.014; 

const byte n_words = 50; // maximum nuber of words in recieved messege
String words[n_words]; // array of string to read from serial port to
unsigned int words_number = 0; // number of words in last recieved command
unsigned int n_sequences, n_new_sequences;
String edge_sequence[n_words];
String channel_string;
byte  int_arr_current_length, current_edge = 0;

String ws, ws0;
String full, tail, msg;
int i = 0, k = 0, j = 0 ;
char b;

// -------    1ms timer ----------------
unsigned long ms_timer = 0;
unsigned long next_ms_time = 0;
bool timeout = false;
void startTimer(){
    cli();// отключить глобальные прерывания    
    TCCR1A = 0; // установить регистры в 0
    TCCR1B = 0;
    TCCR1B |= (1 << WGM12); // включение в CTC режим
    TCCR1B |= (1 << CS10);
    OCR1A = 16000; // установка таймера на 1 мс
    TIMSK1 |= (1 << OCIE1A);  // включение прерываний по совпадению
    sei();
    ms_timer = 0;
    //Serial.println("Timer started");
}
void stopTimer(){
    TCCR1A = 0;
    TCCR1B = 0; // stop timer
}
ISR(TIMER1_COMPA_vect){
    ms_timer++;
    //Serial.println(ms_timer);
    if (ms_timer == next_ms_time){
        //Serial.println("IN MSTIMER");
        timeout = true;
    }
}

// ------ external trigger on pin 2 - start sequence -----
unsigned long t; // variable to read millis()
unsigned long last_trigger_time = 0; // last time when triggered
bool triggered=false;
void interrupt_handler(){
  t = millis();
  if (t - last_trigger_time > 10){ // it is not a noise
    last_trigger_time = t;
    triggered=true; // rise flag
  }
}


// -------------- initialization -----------------------------
int available_ports[] = {A0, 12, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, A1, A2, A3, A4, A5};
const int ports_number = 17;
unsigned long interrupt_counter;
void setup() {
    Serial.begin(115200); // boud rate 
    attachInterrupt(0,interrupt_handler,RISING);//connect trigger on pin 2
    for (i = 0; i < ports_number; i++) {
      pinMode(available_ports[i], OUTPUT); // configure output shutter pins
  }
    interrupt_counter = 0;
}

void loop() {
    // startTimer();
    if (Serial.available()>0) {
        data_input_handler();
    }
    if (triggered){
        startTimer();  
        triggered=false; // clear flag
        current_edge = 0;
        write_channels(); // call routine
        interrupt_counter += 1;
        if (debug == 1){
            Serial.print(String("i" + String(interrupt_counter))); // indication of a trigger
//          Serial.println(i);
        }
    }
    if (timeout){
        timeout=false;
        write_channels(); // call routine
    }

}

unsigned int current_shutters_state;
// writing beam shutter states 
void write_channels(){
    if (n_sequences == 0){
      return;
    }
    ws = edge_sequence[current_edge]; // read current state as string
    current_shutters_state = ws.substring(ws.indexOf("_")+1).toInt();
    if (debug == 2 or debug == 10 ){
      Serial.print("Shutters state");
      Serial.println(current_shutters_state);
    }
    int_arr_current_length = channel_string.length(); // save length of channel_number or state array for current sequence
    //  Serial.print("Start writing time ");
    //  Serial.println(micros());
    for (int i=0;i<int_arr_current_length;i++){
       digitalWrite(available_ports[channel_string.substring(i,i+1).toInt()], 
                  (current_shutters_state >> (int_arr_current_length-i-1)) %2); // write state to beam shutter output pin
       if (debug == 2 or debug == 10 ){
          Serial.print(channel_string.substring(i,i+1).toInt());
          Serial.print(" state ");
          Serial.print( (int_arr_current_length >> (int_arr_current_length-i-1)) %2 );
          Serial.print(",   ");
      }
   }
   //  Serial.print("End writing time ");
    current_edge += 1;
    if (current_edge < n_sequences){
        ws = edge_sequence[current_edge]; //new string of beam shutters state
        //    Serial.println(ws);
        next_ms_time = int(ws.substring(0,ws.indexOf("_")).toInt()/second_coefficient);
    }
    else{
        //Serial.println("STOP TIMER");
        stopTimer();
    }
}


void data_input_handler() {
  i = get_string_array(); // reads input and separates words
  if (i == -1) {
    if (debug > 9 ) {
      Serial.print("Bad command, n words");
      Serial.println(words_number);
    }
    return;
  }

  if ( (words[0]).equals("*IDN") ) { // identification
    Serial.println("ArduinoShutters_v4.1");
  }
    
  if ( (words[0]).equals("debug") ) { // set debug mode
    if  (words_number == 2) {
      debug = words[1].toInt();
      Serial.println("Debug state updated");
    }
    else {
      Serial.println("incorrect command");
    }
   }

   if ( (words[0]).equals("BS") ) { // saves all sequences to edge_sequence array of string
        // BS 123 0_1!
        if (words[1].indexOf("_")!=-1){ // second part of the command
          n_new_sequences = words_number - 1;
          for (int i = 0; i < n_new_sequences; i++){ // writing
            //     Serial.print(i-1);
            //     Serial.println(words[i]);
            edge_sequence[n_sequences + i] = words[i+1];
        }
        n_sequences += n_new_sequences;
        }
        else {
        for (int i = 0; i < n_words; i++) {
          edge_sequence[i] = "";
        }
        channel_string = words[1];
        n_sequences = words_number-2; // number of edges
        for (int i = 2; i < words_number; i++){ // writing
            //     Serial.print(i-1);
            //     Serial.println(words[i]);
            edge_sequence[i-2] = words[i];
        }
        }     
        //   for (int i = 0; i < n_sequences; i++){  
        //    Serial.print(i);     
        //    Serial.println(edge_sequence[i]);
        //    }
    if (debug > 0 ){
      Serial.println("BS Ok");
    }
 }
}

int get_string_array(){
  delay(10);
  //detachInterrupt(0); // it was an idea that some problems are due to the interrupt, but they are not
  full = "";
  words_number=0;
  for (int i = 0; i < n_words; i++) {
    words[i] = "";
  }
  k = 0;
  i = 30000; // numbers to try read serial input
  while (i > 0) {
    b = char(Serial.read());
    if (b == '!' or b == '?') {
//      Serial.println(i);
      break;
    }
    else if (b == ' ') {
      k++;
    }
    else if (b >= 0) {
      words[k] += b;
    }
    i--;
  }
  if (i == 0) {
//    attachInterrupt(0, interrupt_handler, RISING);
    return -1;
  }
  words_number = k + 1;
  return 0;
}
