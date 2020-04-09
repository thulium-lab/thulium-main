#include <SPI.h>
#include <EEPROM.h>  
#include <avr/io.h>
#include <avr/interrupt.h>


int debug = 1;
bool first_run = true;
bool check_mux = false;

const byte N_DAC = 5;
const int ch0pol_pin = 8;
const byte n_words = 50; // maximum nuber of words in recieved messege
String words[n_words]; // array of string to read from serial port to
int words_number = 0; // number of words in last recieved command

unsigned int edge_times[20];
String edge_data[20];
String ws, ws0;
byte current_edge = 0;
unsigned int n_pulses = 0;
byte channel = 0;

String full, tail, msg;
int i = 0, k = 0, j = 0 ;
char b;

// -------    1ms timer ----------------
unsigned long ms_timer = 0;
unsigned long next_ms_time = 0;
unsigned long mux_last_check_time = 0;
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
//    Serial.println("Timer started");
}
void stopTimer(){
    TCCR1A = 0;
    TCCR1B = 0; // stop timer
}
ISR(TIMER1_COMPA_vect){
    ms_timer++;
    mux_last_check_time++;
//    if (ms_timer%100 == 0){
//      Serial.println(ms_timer);
//    }
    if (ms_timer == next_ms_time){
//        Serial.print("IN MSTIMER ");
//        Serial.println(ms_timer);
        timeout = true;
    }
    if (mux_last_check_time > 2000){
        check_mux = true;
    }
}

unsigned long t; // variable to read millis()
unsigned long last_trigger_time = 0; // last time when triggered
bool triggered=false;

// ------ external trigger on pin 2 - start sequence -----
void interrupt_handler(){
  t = millis();
  if (t - last_trigger_time > 10){ // it is not a noise
    last_trigger_time = t;
    triggered=true; // rise flag
  }
}

// --------------  SPI communication  ------------------------
#define SPI_DEBUG 3
const int slaveSelectPin = 10;
byte address = 1;
byte command = 2;
int value = 10;
byte fault_reg, comm_and_addr,val1, val0; // bytes to read from spi
byte old_comm_and_addr; // bytes which have been sent to SPI before
unsigned int old_val;
void handleFaultReg(byte fr){
    if (fr){
        Serial.print("Fault Register = ");
        Serial.println(fr,BIN);
        }
}
void writeSPI32(byte command, byte address, unsigned int value) {
    // take the SS pin low to select the chip:
    digitalWrite(slaveSelectPin, LOW);
    //  send in the address and value via SPI:
    fault_reg = SPI.transfer(0);
    comm_and_addr = SPI.transfer((command << 4) + address);
    val1 = SPI.transfer(value>>8);
    val0 = SPI.transfer(value);
    // take the SS pin high to de-select the chip:
    digitalWrite(slaveSelectPin, HIGH);
    // check that there is no error and previously sent command
    if (debug==SPI_DEBUG){
        handleFaultReg(fault_reg);
        if (comm_and_addr != old_comm_and_addr){
            //Serial.print("c_a_err:w,r: "); Serial.print(old_comm_and_addr,BIN); //Serial.print("\t"); Serial.println(comm_and_addr,BIN);
        }
      if (((int(val1))*(2^8) + val0) != old_val){
        //Serial.print("val_err:w,r: "); Serial.print(old_val, BIN); //Serial.print("\t"); Serial.println((int(val1))*(2^8) + val0,BIN);
      }
      old_val = value;
      old_comm_and_addr = comm_and_addr;
    }
  
  
}

// --------------- LTC2662 current channels -----------------
class Channel{
    byte channel;
    unsigned long range; // im uamps
    byte sign; // 0 - "+" polarity, 1 - "-" polarity
    float current;
    byte on;
    byte pol_pin;
    bool pol_changed = false;
    float mux_current;
public:
    Channel(byte a_channel=0,unsigned long a_range=300,byte a_sign=0,float a_current=0,byte a_on=1, byte a_pol_pin=8){
        channel = a_channel;
        range = a_range;
        sign = a_sign;
        current = a_current;
        on = a_on;
        pol_pin = a_pol_pin;
  }
    
    void setRange(unsigned long new_range){
    range = new_range;
    if (current*1000 > range){
      current = float(range)/1000;
    }
  }
    
    void setCurrent(float new_current){
        //Serial.print("New current ");
        //Serial.println(new_current);
    if (new_current==0){
      sign = 0;
      current = 0;
      on=0;
    }
    else{
      if ((new_current>0)==sign){
        pol_changed=true;
        if (sign==0){
            sign =1;
        }
          else{
            sign =0;
          }
      }
      if (abs(new_current)*1000 > range){
        current = float(range)/1000;
      }
      else{
        current = abs(new_current);
      }
      on = 1;
    }
  }
    
    bool isOn(){
        return on;
    } 
    
    byte getRangeCode(){
        switch (range){
            case 3125:
                return B1;
            case 6250:
                return B10;
            case 12500:
                return B11;
            case 25000:
                return B100;
            case 50000:
                return B101;
            case 100000:
                return B110;
            case 200000:
                return B111;
            case 300000:
                return B1111;
            default:
                return B110;
                
        }
    }
    
    float getCurrent(){
        return current;
    }
    
    unsigned int getCurrentCode(){
        return (unsigned int)((current*1000/range)*65535);
    }
    
    byte getPolPin(){
        return pol_pin;
    }
    
    void writeRange(unsigned long new_range){
        //Serial.println(String("Channel range set" + String(channel) + String(range)));
        setRange(new_range);
        writeSPI32(B0110,channel,getRangeCode());
        writeCurrent(current);
}
    
    void writeCurrent(float new_current){
        //Serial.print("current ");Serial.println(current);
        setCurrent(new_current);
        if ((on==0) || (current==0)){
            writeSPI32(B0100,channel,0); // power down channel
            digitalWrite(pol_pin,sign);
                pol_changed = false;
            return;
        }
        else{
            if (pol_changed){
                writeSPI32(B0110,channel,getRangeCode());
                digitalWrite(pol_pin,sign);
                pol_changed = false;
            }
            writeSPI32(B0,channel,getCurrentCode()); // write current to register
        }
        update(); // update channel's output
}
    
    void update(){
        writeSPI32(B1,channel,0);
    }
    
    String checkCurrent(int value){
        mux_current = 1.1*(1.0*range/1000) * (5.0*value/1023 ) / 1.25;
        //Serial.print("Mux current ");
        //Serial.println(mux_current);
        if (abs(mux_current - current)/(current+1) < 0.2){
//            return String("Ok Ch" + String(channel) + ", Is=" + String(current) + ", Ir=" + String(mux_current));
            return String(" " + String(channel) + "," + String(current,1) + "," + String(mux_current,0)) + ",";
        }
        else{
//            return String("Bd Ch" + String(channel) + ", Is=" + String(current) + ", Ir=" + String(mux_current));
            return String(" " + String(channel) + "," + String(current,1) + "," + String(mux_current,0)) + ",";
        }
        
    }
    
    String str(){
        return String("range=" + String(range) + "uA, sing=" + String(sign) + 
                      ",current=" + String(current) + "mA, on=" + String(on) +
                      ",pol_pin=" + String(pol_pin));
    }
    
};

Channel channels[5];

// -------------- reading LTC2662 analog data ---------------
byte mux_counter;
int mux_pin = A0;
int mux_value = 0;
float die_temp;
void checkMux(){
    // check currents
    mux_last_check_time = 0;
    msg = "";
    // check temperature
    writeSPI32(B1011,0,B1010);
    delay(1);
    mux_value = analogRead(mux_pin);
    //Serial.println(mux_value);
    die_temp = 25.0 + (1.4-5.0*mux_value/1023)/0.0037;
    msg += String("T=" + String(die_temp));
    for (int i=0;i<N_DAC;i++){
//        Serial.print("Temperature: ");
//        Serial.println(die_temp);
//        delay(2);
        if (channels[i].isOn()){
            writeSPI32(B1011,0,i+1);
            delay(1);
            mux_value = analogRead(mux_pin);
            //Serial.println(mux_value);
//            delay(2);
            msg += channels[i].checkCurrent(mux_value);
            writeSPI32(B1011,0,i+24);
            delay(1);
            mux_value = analogRead(mux_pin);
//            delay(2);
//            msg += String(" V=" + String(5.0*mux_value/1023));
            msg += String(5.0*mux_value/1023,1);
//            Serial.println(msg);
        }
//        else{
//            Serial.println(String("off Ch" + String(i)));
//        }
    }
    Serial.println(msg);
}

// -------------- initialization -----------------------------
unsigned long range; // im uamps
byte sign; // 0 - "+" polarity, 1 - "-" polarity
float current;
byte on;
unsigned long interrupt_counter;

void setup() {
    interrupt_counter = 0;
    Serial.begin(115200); // boud rate 
    pinMode (slaveSelectPin, OUTPUT);
    SPI.begin(); // initialize SPI:
    attachInterrupt(0,interrupt_handler,RISING);//connect trigger on pin 2
    // initialize Channels
    for (int i=0;i<N_DAC;i++){
        if (first_run == false){
            EEPROM.get(10*i, range);
            EEPROM.get(10*i+4, sign);
            EEPROM.get(10*i+5, current);
            EEPROM.get(10*i+9, on);
        }
        else{
            range = 100000;
            sign = 0;
            current = 0;
            on = 0;
        }
        channels[i] = Channel(i,range,sign,current,on,8-i);
        pinMode(8-i,OUTPUT);
        digitalWrite(8-i,on);
        channels[i].writeRange(range);
        channels[i].writeCurrent(current);
        // Serial.println(channels[i].str());
    }
}

void loop() {
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
            Serial.println(String("i" + String(interrupt_counter))); // indication of a trigger
        }
        checkMux();
    }
    if (timeout){
        timeout=false;
        write_channels(); // call routine
    }
    if (check_mux){
        check_mux = false;
//        checkMux();
    }
    //checkMux();

}

void write_channels(){
    if (n_pulses == 0){
        //Serial.println("No pulses");
        return;
    }
    ws = edge_data[current_edge]; // read current state as string
    for (int i=0;i<5;i++){ // maximum channels data is 5
        k = ws.indexOf(",");
        if (k==-1){
            ws0 = ws;
            ws = "";
        }
        else{
            ws0=ws.substring(0,k);
            ws = ws.substring(k+1);
        }
        channel = (ws0.substring(0,1)).toInt();
        current = (ws0.substring(2)).toFloat();
        channels[channel].writeCurrent(current);
        if (ws==""){
            break;
        }
    }
    current_edge +=1;
//      Serial.print("New current edge ");Serial.println(current_edge);
    
    
    if (current_edge < n_pulses){
//      Serial.println(edge_times[current_edge]);
        next_ms_time = edge_times[current_edge];
    }
    else{
//        Serial.println("STOP TIMER");
        stopTimer();
    }
}

void data_input_handler() {
  i = get_string_array(); // reads input and separates words
  if (i == -1) {
    if (debug > 9 ) {
      Serial.print("Bd, n_w");
      Serial.println(words_number);
    }
    return;
  }
//  handled = false;

  if ( (words[0]).equals("*IDN") ) { // identification
    Serial.println("ArduinoCurrent_0");
  }
    
  if ( (words[0]).equals("debug") ) { // set debug mode
    if  (words_number == 2) {
      debug = words[1].toInt();
      Serial.println("Debug state updated");
    }
    else {
      Serial.println("incorrect command debug");
    }
  }
    
  if ( (words[0]).equals("range") ) { // set state of wavelength meter shutters
    if (words_number == 3) { // check if input more or less correct
        i = words[1].toInt();
        range = (unsigned long)words[2].toFloat();
        channels[i].writeRange(range);
//        Serial.println(String("range " + words[1] + " " + words[2]));
        return;
    }
    else{
        Serial.println("incorrect command range");
    }
  }

    if ( (words[0]).equals("all_ranges") ) { // set state of wavelength meter shutters
    if (words_number == 6) { // check if input more or less correct
        for(i=0;i<5;i++){
            range = (unsigned long)words[i+1].toFloat();
            channels[i].writeRange(range);  
        }
//        Serial.println("all_ranges updated");
        return;
    }
    else{
        Serial.println(String("incorrect command"+words[0]));
    }
  }
    
  if ( (words[0]).equals("current") ) { // set state of wavelength meter shutters
    if (words_number == 3) { // check if input more or less correct
        i = words[1].toInt();
        current = words[2].toFloat();
        channels[i].writeCurrent(current);
//        Serial.println(String("current " + words[1] + " " + words[2]));
        return;
    }
    else{
        Serial.println("incorrect command current");
    }
  }

  if ( (words[0]).equals("all_currents") ) { // set state of wavelength meter shutters
    if (words_number == 6) { // check if input more or less correct
        for(i=0;i<5;i++){
            current = words[i+1].toFloat();
            channels[i].writeCurrent(current);  
        }
//        Serial.println("all_currents updated");
        return;
    }
    else{
        Serial.println(String("incorrect command"+words[0]));
    }
  }
    
    if ( (words[0]).equals("pulse") ) { // saves pulses times to edge_times and channels:currents to string
    //  test command 
    // pulses 0 0:12,1:10 400 0:50,1:30!
        if (words_number==1){
            n_pulses = 0;
            Serial.println("n_pulses = 0");
            return;
        }
        if (words[1] == "0"){ // the first edge of the pulse
            //Serial.println("0-pulse");
            n_pulses = 1;
        }
        else{
            //Serial.println("next-pulse");
            n_pulses++;
        }
        edge_times[n_pulses-1] = words[1].toInt();
        edge_data[n_pulses-1] = words[2];
//        Serial.println(String("pulse " + words[1] + " " + words[2]));
        
    }
}

int get_string_array(){
  delay(1);
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
