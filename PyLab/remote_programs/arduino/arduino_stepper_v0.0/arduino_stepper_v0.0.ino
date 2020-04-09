#include <AFMotor.h>

//#include <SPI.h>
//#include <EEPROM.h>  
#include <avr/io.h>
#include <avr/interrupt.h>


int debug = 1;
bool first_run = true;

const double second_coefficient = 1.014; 

const byte n_words = 50; // maximum nuber of words in recieved messege
String words[n_words]; // array of string to read from serial port to
unsigned int words_number = 0; // number of words in last recieved command
unsigned int n_sequences;
String edge_sequence[n_words];
String channel_string;
byte  int_arr_current_length, current_edge = 0;

String ws, ws0;
String full, tail, msg;
int i = 0, k = 0, j = 0 ;
char b;

// -------    1ms timer ----------------
//unsigned long ms_timer = 0;
//unsigned long next_ms_time = 0;
//bool timeout = false;
//void startTimer(){
//    cli();// отключить глобальные прерывания    
//    TCCR1A = 0; // установить регистры в 0
//    TCCR1B = 0;
//    TCCR1B |= (1 << WGM12); // включение в CTC режим
//    TCCR1B |= (1 << CS10);
//    OCR1A = 16000; // установка таймера на 1 мс
//    TIMSK1 |= (1 << OCIE1A);  // включение прерываний по совпадению
//    sei();
//    ms_timer = 0;
//    //Serial.println("Timer started");
//}
//void stopTimer(){
//    TCCR1A = 0;
//    TCCR1B = 0; // stop timer
//}
//ISR(TIMER1_COMPA_vect){
//    ms_timer++;
//    //Serial.println(ms_timer);
//    if (ms_timer == next_ms_time){
//        //Serial.println("IN MSTIMER");
//        timeout = true;
//    }
//}

// ------ external trigger on pin 2 - start sequence -----
//unsigned long t; // variable to read millis()
//unsigned long last_trigger_time = 0; // last time when triggered
//bool triggered=false;
//void interrupt_handler(){
//  t = millis();
//  if (t - last_trigger_time > 10){ // it is not a noise
//    last_trigger_time = t;
//    triggered=true; // rise flag
//  }
//}

AF_Stepper stepper0(200,1);
AF_Stepper stepper1(200,2);

// -------------- initialization -----------------------------
unsigned long interrupt_counter;
void setup() {
    Serial.begin(115200); // boud rate 
    stepper0.setSpeed(30);
    stepper1.setSpeed(30);
//    attachInterrupt(0,interrupt_handler,RISING);//connect trigger on pin 2
//    interrupt_counter = 0;
}

void loop() {
    // startTimer();
    if (Serial.available()>0) {
        data_input_handler();
    }
//    if (triggered){
//        startTimer();  
//        triggered=false; // clear flag
//        current_edge = 0;
//        write_channels(); // call routine
//        interrupt_counter += 1;
//        if (debug == 1){
//            Serial.print(String("i" + String(interrupt_counter))); // indication of a trigger
//        }
//    }
//    if (timeout){
//        timeout=false;
//        write_channels(); // call routine
//    }

}

unsigned int current_shutters_state;
// writing beam shutter states 
byte direct;
int n_steps;
String channel;

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
    Serial.println("ArduinoStepper_v0.0");
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

   if ( (words[0]).equals("move") ) { // saves all sequences to edge_sequence array of string
        // move 1 100!
        if (words_number != 3) {
          Serial.println("Bad command move");
          return;
        }
        channel = words[1];
        n_steps = words[2].toInt();
        if (n_steps < 0){
          direct = BACKWARD;
        }
        else {
          direct = FORWARD;
        }
        if (channel=="0"){
          stepper0.step(abs(n_steps),direct,SINGLE);
        }
        else {
          stepper1.step(abs(n_steps),direct,SINGLE);
        }
    if (debug > 0 ){
      Serial.println("Moved");
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
