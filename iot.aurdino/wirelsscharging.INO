#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP_Mail_Client.h>
#include <LiquidCrystal_I2C.h>

// WiFi Configuration
#define WIFI_SSID "Park&Power"
#define WIFI_PASSWORD "123456789"

// Email Configuration
#define SMTP_HOST "smtp.gmail.com"
#define SMTP_PORT 465
#define AUTHOR_EMAIL "mosin@gmail.com"
#define AUTHOR_PASSWORD "refer youtub for the code 
#define RECIPIENT_EMAIL "park.and.power.project@gmail.com"

// Hardware Configuration
#define SS_PIN 5
#define RST_PIN 26
#define IR_SLOT1 4
#define IR_SLOT2 13
#define LED_SLOT1 15
#define LED_SLOT2 2

// I2C LCD Configuration
#define LCD_ADDRESS 0x27
#define LCD_COLUMNS 16
#define LCD_ROWS 2

MFRC522 mfrc522(SS_PIN, RST_PIN);
SMTPSession smtp;
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLUMNS, LCD_ROWS);

struct ParkingSlot {
  unsigned long entryTime = 0;
  bool occupied = false;
  bool previousState = false;
  String vehicleNumber = "";
  String phoneNumber = "";
};

ParkingSlot slot1, slot2;
bool systemActive = false;
bool wifiConnected = false;
unsigned long lastDisplayUpdate = 0;
unsigned long lastRFIDCheck = 0;

void setup() {
  Serial.begin(115200);
  
  // Initialize hardware
  SPI.begin();
  mfrc522.PCD_Init();
  
  pinMode(IR_SLOT1, INPUT_PULLUP);
  pinMode(IR_SLOT2, INPUT_PULLUP);
  pinMode(LED_SLOT1, OUTPUT);
  pinMode(LED_SLOT2, OUTPUT);
  
  digitalWrite(LED_SLOT1, LOW);
  digitalWrite(LED_SLOT2, LOW);

  // Initialize LCD
  lcd.begin();
  lcd.backlight();
  displayWelcomeMessage();

  // Start WiFi connection
  connectWiFi();
  
  // Initial sensor reading
  slot1.previousState = digitalRead(IR_SLOT1);
  slot2.previousState = digitalRead(IR_SLOT2);
  
  // Generate initial vehicle data
  generateVehicleData(slot1);
  generateVehicleData(slot2);
}

void loop() {
  // Only proceed if WiFi is connected and system is active
  if (!wifiConnected) {
    displayWiFiStatus();
    delay(1000);
    return;
  }
  
  if (!systemActive) {
    checkRFID();
    return;
  }

  // Check both slots
  checkSlot(1, IR_SLOT1, LED_SLOT1, slot1);
  checkSlot(2, IR_SLOT2, LED_SLOT2, slot2);

  // Update display periodically
  if (millis() - lastDisplayUpdate > 1000) {
    updateDisplay();
    lastDisplayUpdate = millis();
  }
}

void checkRFID() {
  if (millis() - lastRFIDCheck < 500) return;
  lastRFIDCheck = millis();
  
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    systemActive = true;
    displaySystemActivated();
    mfrc522.PICC_HaltA();
  }
}

void connectWiFi() {
  lcd.clear();
  lcd.print("Connecting WiFi");
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long startTime = millis();
  
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 10000) {
    delay(500);
    lcd.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    lcd.clear();
    lcd.print("WiFi Connected");
    lcd.setCursor(0, 1);
    lcd.print("Scan RFID Card");
    delay(2000);
  } else {
    wifiConnected = false;
    lcd.clear();
    lcd.print("WiFi Failed");
    delay(2000);
  }
}

void displayWiFiStatus() {
  lcd.clear();
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    lcd.print("WiFi Connected");
    lcd.setCursor(0, 1);
    lcd.print("Scan RFID Card");
  } else {
    wifiConnected = false;
    lcd.print("WiFi Disconnected");
    lcd.setCursor(0, 1);
    lcd.print("Reconnecting...");
    connectWiFi();
  }
}

void checkSlot(int slotNum, int irPin, int ledPin, ParkingSlot &slot) {
  bool currentState = digitalRead(irPin);
  
  if (currentState != slot.previousState) {
    if (currentState == LOW && !slot.occupied) {
      // Vehicle entered
      slot.occupied = true;
      slot.entryTime = millis();
      digitalWrite(ledPin, HIGH);
      generateVehicleData(slot);
      
      lcd.clear();
      lcd.print("Slot ");
      lcd.print(slotNum);
      lcd.print(": Occupied");
      delay(2000);
    }
    else if (currentState == HIGH && slot.occupied) {
      // Vehicle left
      unsigned long parkedTime = (millis() - slot.entryTime) / 1000;
      float total = (parkedTime / 10.0) * 1.18; // ₹1 per 10 sec + 18% GST
      
      slot.occupied = false;
      digitalWrite(ledPin, LOW);
      
      // Improved charge display
      lcd.clear();
      lcd.print("Slot ");
      lcd.print(slotNum);
      lcd.print(" Payment");
      lcd.setCursor(0, 1);
      
      // Format time nicely
      unsigned int hours = parkedTime / 3600;
      unsigned int minutes = (parkedTime % 3600) / 60;
      unsigned int seconds = parkedTime % 60;
      
      lcd.print("Time:");
      if (hours > 0) {
        lcd.print(hours);
        lcd.print("h ");
      }
      if (minutes > 0 || hours > 0) {
        lcd.print(minutes);
        lcd.print("m ");
      }
      lcd.print(seconds);
      lcd.print("s");
      
      delay(2000);
      
      // Show charge in second screen
      lcd.clear();
      lcd.print("Parking Charge");
      lcd.setCursor(0, 1);
      lcd.print("Rs.");
      lcd.print(total, 1); // Show with 1 decimal place
      lcd.print(" (incl GST)");
      
      delay(2000); // Show charge for longer
      
      if (parkedTime > 0) {
        sendDepartureEmail(slotNum, parkedTime, total, slot);
      }
    }
    slot.previousState = currentState;
  }
}

void generateVehicleData(ParkingSlot &slot) {
  String letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  String numbers = "0123456789";
  
  slot.vehicleNumber = "";
  slot.vehicleNumber += letters.charAt(random(letters.length()));
  slot.vehicleNumber += letters.charAt(random(letters.length()));
  slot.vehicleNumber += "-";
  slot.vehicleNumber += random(10);
  slot.vehicleNumber += random(10);
  slot.vehicleNumber += "-";
  slot.vehicleNumber += letters.charAt(random(letters.length()));
  slot.vehicleNumber += letters.charAt(random(letters.length()));
  slot.vehicleNumber += "-";
  slot.vehicleNumber += random(10);
  slot.vehicleNumber += random(10);
  slot.vehicleNumber += random(10);
  slot.vehicleNumber += random(10);
  
  slot.phoneNumber = "+91";
  for (int i = 0; i < 10; i++) {
    slot.phoneNumber += numbers.charAt(random(numbers.length()));
  }
}

void sendDepartureEmail(int slotNum, unsigned long parkedTime, float total, ParkingSlot &slot) {
  // Don't show email sending on LCD as per request
  if (WiFi.status() != WL_CONNECTED) return;

  ESP_Mail_Session session;
  session.server.host_name = SMTP_HOST;
  session.server.port = SMTP_PORT;
  session.login.email = AUTHOR_EMAIL;
  session.login.password = AUTHOR_PASSWORD;

  SMTP_Message message;
  message.sender.name = "Smart Parking System";
  message.sender.email = AUTHOR_EMAIL;
  message.subject = "Vehicle Departure Alert - Slot " + String(slotNum);
  message.addRecipient("Admin", RECIPIENT_EMAIL);

  String text = "Vehicle Departure Details:\n\n";
  text += "Parking Slot: " + String(slotNum) + "\n";
  text += "Vehicle Number: " + slot.vehicleNumber + "\n";
  text += "Contact Number: " + slot.phoneNumber + "\n";
  text += "Entry Time: " + formatTime(slot.entryTime) + "\n";
  text += "Exit Time: " + formatTime(millis()) + "\n";
  text += "Duration: " + String(parkedTime) + " seconds\n";
  text += "Total Charge: ₹" + String(total, 2) + " (incl. GST)\n";
  text += "\nThank you for using our parking service!";
  
  message.text.content = text.c_str();

  if (!smtp.connect(&session)) return;
  
  MailClient.sendMail(&smtp, &message);
  smtp.closeSession();
}

void displayWelcomeMessage() {
  lcd.clear();
  lcd.print("  Park & Power ");
  lcd.setCursor(0, 1);
  lcd.print(" System  V1.0");
  delay(2000);
}

void displaySystemActivated() {
  lcd.clear();
  lcd.print("System Active");
  lcd.setCursor(0, 1);
  lcd.print("Monitoring...");
  delay(2000);
}

void updateDisplay() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Slot1: ");
  lcd.print(slot1.occupied ? "Occupied" : "Empty  ");
  
  lcd.setCursor(0, 1);
  lcd.print("Slot2: ");
  lcd.print(slot2.occupied ? "Occupied" : "Empty  ");
}

String formatTime(unsigned long millisTime) {
  time_t now = millisTime / 1000;
  struct tm * timeinfo = localtime(&now);
  char buffer[20];
  strftime(buffer, 20, "%H:%M:%S", timeinfo);
  return String(buffer);
}