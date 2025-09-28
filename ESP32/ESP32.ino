/*
  LugeRelay - Standalone Hardware Timing Test for Seeed XIAO ESP32S3 Sense

  Board: Seeed XIAO ESP32S3 Sense (Arduino-ESP32 core)
  Serial: 115200 baud

  Purpose:
  - Drive a relay to open race gates
  - Wait for a SICK photoelectric sensor (via DFRobot DFR0911 opto-isolator) to trip
  - Measure elapsed time between relay activation and sensor trip using micros()
  - Print structured, timestamped logs with 0.01 s (hundredths) resolution

  IMPORTANT PIN NOTE:
  - Use Arduino pin names (D0..D10) for XIAO ESP32S3 Sense, NOT raw GPIO numbers.
  - Map these to your exact pins per the official Seeed XIAO ESP32S3 Sense pinout.
  - Update PIN_RELAY and PIN_SENSOR below as needed.
*/

#include <Arduino.h>

// =========================
// User Configuration
// =========================

// Pin mapping (Arduino pin names)
constexpr int PIN_RELAY   = D1;   // default; change as needed per XIAO ESP32S3 pinout
constexpr int PIN_SENSOR  = D2;   // default; input from DFR0911 OUT
// LED functionality removed for simplicity

// UART pin definitions for XIAO ESP32S3 (GPIO serial communication)
#define RX_PIN D7
#define TX_PIN D6
#define BAUD 115200

// Polarity configuration
constexpr bool RELAY_ACTIVE_HIGH = true;  // set false for active-LOW relay boards
constexpr bool SENSOR_ACTIVE_LOW = true;  // DFR0911 open-collector sinking -> active LOW

// Behavior configuration
constexpr uint32_t AUTO_START_DELAY_MS = 2000;   // set to 0 or disable via AUTO_START_ENABLED when integrating with Pi
constexpr bool     AUTO_START_ENABLED  = false;   // disable auto-start when controlled by Raspberry Pi
constexpr uint32_t TRIP_TIMEOUT_MS     = 10000;
constexpr uint32_t DEBOUNCE_US         = 4000;   // 4 ms debounce
constexpr bool     RELAY_OFF_AFTER_TRIP = true;  // turn relay off after sensor trips
constexpr uint32_t RELAY_ON_DURATION_MS = 1000;  // relay auto-off after 1 s

// =========================
// Helpers: time and logging
// =========================

static inline uint32_t nowMs() { return millis(); }
static inline uint64_t nowUs() { return micros(); }



// =========================
// ISR-shared state (volatile)
// =========================

// Trip capture
volatile bool g_acceptTrip = false;            // ISR should only capture trips after relay ON
volatile bool g_tripCaptured = false;          // ISR sets true when first valid trip captured
volatile uint64_t g_tTripUs = 0;               // ISR writes timestamp of trip (micros)

// Debounce tracking
volatile bool g_lastLogicalActive = false;     // last logical state as interpreted via SENSOR_ACTIVE_LOW
volatile uint64_t g_lastIsrChangeUs = 0;       // last time a logical edge was processed

// =========================
// Run-state variables
// =========================

enum class RunState : uint8_t {
  IDLE,
  WAIT_TRIP,
  DONE
};

RunState g_state = RunState::IDLE;

// Relay state tracking
bool g_relayOn = false;                        // desired logical ON/OFF (pre-polarity)

// Timing
uint64_t g_tRelayOnUs = 0;                     // timestamp when relay turned ON (micros)
uint32_t g_deadlineMs = 0;                     // deadline for timeout while waiting for trip
uint32_t g_relayOffAtMs = 0;                   // scheduled time to turn relay OFF

// Scheduling
bool     g_autoStarted = false;                // auto-start only once after boot
uint32_t g_bootMs = 0;                         // time at boot
uint32_t g_nextHeartbeatMs = 0;                // 1 Hz heartbeat when idle

// Serial input buffer (simple line buffer)
String g_lineBuf;

// =========================
// Forward declarations
// =========================

void IRAM_ATTR onSensorChange();
void armSensor();
void disarmSensor();
void setRelay(bool on);
void startRun();
void finishRunSuccess(uint64_t tRelayOnUs, uint64_t tTripUs);
void finishRunTimeout();
void transitionToIdleAndAnnounce();

// =========================
// ISR: sensor change with debounce and logic mapping
// =========================

void IRAM_ATTR onSensorChange() {
  // Debounced edge detection on the logical sensor state
  const uint64_t tNow = nowUs();

  // Edge-rate limit (simple debounce window)
  if ((tNow - g_lastIsrChangeUs) < DEBOUNCE_US) {
    return;
  }

  const int rawLevel = digitalRead(PIN_SENSOR);
  const bool logicalActive = SENSOR_ACTIVE_LOW ? (rawLevel == LOW) : (rawLevel == HIGH);

  if (logicalActive != g_lastLogicalActive) {
    g_lastLogicalActive = logicalActive;
    g_lastIsrChangeUs = tNow;

    // Capture only first valid ACTIVE edge after relay ON
    if (logicalActive && g_acceptTrip && !g_tripCaptured) {
      g_tTripUs = tNow;
      g_tripCaptured = true;
      // Do not detach interrupt in ISR; main loop will handle it.
    }
  }
}

// =========================
// Hardware helpers
// =========================

void setRelay(bool on) {
  if (g_relayOn == on) {
    // No change
    return;
  }
  g_relayOn = on;
  const bool driveHigh = RELAY_ACTIVE_HIGH ? on : !on;
  digitalWrite(PIN_RELAY, driveHigh ? HIGH : LOW);

  // Log only the activation event as specified
  if (on) {
    Serial1.printf("[EVENT] RELAY_ON t_ms=%lu\n", (unsigned long)nowMs());
  }
}

void armSensor() {
  pinMode(PIN_SENSOR, INPUT_PULLUP);
  // Initialize logical baseline
  const int rawLevel = digitalRead(PIN_SENSOR);
  g_lastLogicalActive = SENSOR_ACTIVE_LOW ? (rawLevel == LOW) : (rawLevel == HIGH);
  g_lastIsrChangeUs = nowUs();
  g_tripCaptured = false;
  g_acceptTrip = false; // will be enabled when relay turns ON
  attachInterrupt(digitalPinToInterrupt(PIN_SENSOR), onSensorChange, CHANGE);
  Serial1.println("[INFO] Armed sensor");
}

void disarmSensor() {
  detachInterrupt(digitalPinToInterrupt(PIN_SENSOR));
}

// =========================
// Run control
// =========================

void startRun() {
  // Arm sensor first
  armSensor();

  // Activate relay and start high-precision timer
  setRelay(true);
  const uint64_t tNow = nowUs();
  // Enable ISR to accept trip only after relay is ON
  g_acceptTrip = true;
  g_tRelayOnUs = tNow;
  g_relayOffAtMs = nowMs() + RELAY_ON_DURATION_MS;

  // Transition state machine
  g_state = RunState::WAIT_TRIP;
  g_deadlineMs = nowMs() + TRIP_TIMEOUT_MS;
}

void finishRunSuccess(uint64_t tRelayOnUs, uint64_t tTripUs) {
  // Stop listening to the sensor during post-processing
  disarmSensor();

  // Optionally turn off relay
  if (RELAY_OFF_AFTER_TRIP) {
    setRelay(false);
  }

  // Log sensor event and elapsed time
  Serial1.printf("[EVENT] SENSOR_TRIPPED t_ms=%lu\n", (unsigned long)nowMs());

  const uint64_t elapsedUs = (tTripUs - tRelayOnUs);
  const double elapsedSec = (double)elapsedUs / 1000000.0;
  Serial1.printf("[RESULT] ELAPSED_s=%.2f\n", elapsedSec);

  // Also print M:SS:MMM (Minutes:Seconds:Milliseconds)
  const uint32_t totalMs = (uint32_t)((elapsedUs + 500ULL) / 1000ULL); // rounded to nearest ms
  const uint32_t minutes = totalMs / 60000U;
  const uint32_t seconds = (totalMs % 60000U) / 1000U;
  const uint32_t millisPart = totalMs % 1000U;
  Serial1.printf("[RESULT] ELAPSED_MSM=%lu:%02lu:%03lu\n",
                (unsigned long)minutes,
                (unsigned long)seconds,
                (unsigned long)millisPart);

  // Print compact SS.MMM for Pi (same info, different format)
  const uint32_t totalSeconds = (minutes * 60U) + seconds;
  Serial1.printf("[RESULT] ELAPSED_SM=%02lu.%03lu\n",
                (unsigned long)totalSeconds,
                (unsigned long)millisPart);

  g_state = RunState::DONE;
}

void finishRunTimeout() {
  // Timeout reached while waiting for sensor
  disarmSensor();
  setRelay(false);
  Serial1.println("[WARN] TIMEOUT waiting for sensor");
  g_state = RunState::DONE;
}

void transitionToIdleAndAnnounce() {
  g_state = RunState::IDLE;
  Serial1.println("[INFO] Ready (type GO to run)");
  // Schedule heartbeat immediately
  g_nextHeartbeatMs = nowMs();
}

// =========================
// Setup and main loop
// =========================

void setup() {
  // Initialize Serial1 with explicit UART pins for GPIO communication
  Serial1.begin(BAUD, SERIAL_8N1, RX_PIN, TX_PIN);
  
  // Also initialize Serial for USB debugging (optional)
  Serial.begin(115200);
  // Give USB CDC a moment (non-blocking pattern)
  unsigned long startWait = millis();
  while (!Serial && (millis() - startWait) < 500) {
    // brief wait for Serial to open; not required
  }

  // Relay output setup
  pinMode(PIN_RELAY, OUTPUT);
  setRelay(false); // ensure relay starts OFF

  // Boot banner
  Serial1.printf(
    "[BOOT] LugeRelay Test | RelayPin=%d ActiveHigh=%d | SensorPin=%d ActiveLow=%d | UART RX=%d TX=%d\n",
    PIN_RELAY, RELAY_ACTIVE_HIGH ? 1 : 0, PIN_SENSOR, SENSOR_ACTIVE_LOW ? 1 : 0, RX_PIN, TX_PIN
  );

  g_bootMs = nowMs();
  g_autoStarted = false;
  g_lineBuf.reserve(32);

  transitionToIdleAndAnnounce();
}

static inline bool shouldAutoStartNow() {
  if (!AUTO_START_ENABLED) return false;
  if (g_autoStarted) return false;
  const uint32_t elapsed = nowMs() - g_bootMs;
  return (elapsed >= AUTO_START_DELAY_MS);
}

static inline void processSerialCommandIfAny() {
  while (Serial1.available() > 0) {
    char c = (char)Serial1.read();
    if (c == '\r') {
      // ignore CR
      continue;
    }
    if (c == '\n') {
      // Process a line
      String cmd = g_lineBuf;
      g_lineBuf = "";
      cmd.trim();
      cmd.toUpperCase();

      // Empty line (Enter) or explicit GO triggers a run when idle
      if (g_state == RunState::IDLE && (cmd.length() == 0 || cmd == "GO")) {
        startRun();
      }
      // Ignore other commands for now (keep output minimal)
    } else {
      if (g_lineBuf.length() < 64) {
        g_lineBuf += c;
      }
    }
  }
}

void loop() {
  // Heartbeat when idle (1 Hz)
  if (g_state == RunState::IDLE) {
    const uint32_t now = nowMs();
    if ((int32_t)(now - g_nextHeartbeatMs) >= 0) {
      Serial1.printf("[STATUS] idle t_ms=%lu\n", (unsigned long)now);
      g_nextHeartbeatMs = now + 1000;
    }

    // Auto-start once after power-up
    if (shouldAutoStartNow()) {
      g_autoStarted = true;
      startRun();
    }
  }

  // Process serial input regardless of state, but only acts when IDLE
  processSerialCommandIfAny();

  // State machine progression
  switch (g_state) {
    case RunState::IDLE:
      // Nothing else; waiting for auto-start or GO
      break;

    case RunState::WAIT_TRIP: {
      // Check for ISR-captured trip
      bool captured = false;
      uint64_t tTrip = 0;
      uint64_t tRelayOn = 0;
      noInterrupts();
      if (g_tripCaptured) {
        captured = true;
        tTrip = g_tTripUs;
        tRelayOn = g_tRelayOnUs; // g_tRelayOnUs is not ISR-written, but keep symmetry
      }
      interrupts();

      // Auto turn relay OFF after configured duration, timer keeps running until sensor trip
      if (g_relayOn && (int32_t)(nowMs() - g_relayOffAtMs) >= 0) {
        setRelay(false);
      }

      if (captured) {
        finishRunSuccess(tRelayOn, tTrip);
        break;
      }

      // Timeout check
      if ((int32_t)(nowMs() - g_deadlineMs) >= 0) {
        finishRunTimeout();
      }
      break;
    }

    case RunState::DONE:
      // Return to idle and announce readiness
      transitionToIdleAndAnnounce();
      break;
  }
}


