#include <Arduino.h>
#include <LittleFS.h>

#define VERSION "3.0-FOPDT"

#define MOTOR_EN 14
#define MOTOR_IN3 26
#define MOTOR_IN4 27

#define ENCODER_A 33
#define ENCODER_B 32

#define PWM_CHANNEL 0
#define PWM_FREQ 5000
#define PWM_RESOLUTION 8

#define MAX_DURATION 15000

#define CALIB_FILE "/calib.bin"
#define PID_FILE "/pid.bin"
#define LRC_FILE "/lrc.bin"
#define MCHAR_FILE "/mchar.bin"

#define MAX_CHAR_POINTS 52
#define SWEEP_STEP 5
#define SWEEP_SETTLE_MS 500

volatile long encoderTicks = 0;
volatile int lastEncoded = 0;

float speedConstant = 1.0;
float maxRPM = 0.0;

int lrcMinPWM = 0;
int lrcMaxPWM = 255;
float lrcMinRPM = 0.0;
float lrcMaxRPM = 0.0;
bool hasLinearRegion = false;

int charPWMValues[MAX_CHAR_POINTS];
float charSpeedValues[MAX_CHAR_POINTS];
int charCount = 0;

float Kp = 0.0;
float Ki = 0.0;
float Kd = 0.0;

enum ControlMode { P_ONLY, PI_CTRL, PD, PID };
ControlMode controlMode = PID;

enum OpMode {
    MODE_IDLE,
    MODE_OPEN_LOOP,
    MODE_CLOSED_LOOP,
    MODE_ENCODER,
    MODE_SPEED_LOG,
    MODE_LINEAR_REGION
};
OpMode opMode = MODE_IDLE;

enum RunState { STATE_IDLE, STATE_RUNNING, STATE_SWEEP };
RunState runState = STATE_IDLE;

int direction = 1;
float setpoint = 0.0;
int samplingMs = 100;
int durationMs = 5000;

unsigned long lastSampleTime = 0;
unsigned long startTime = 0;

float integral = 0.0;
float prevError = 0.0;

int openLoopPWM = 0;

int sweepCurrentPWM = 0;
unsigned long sweepStepStart = 0;

void IRAM_ATTR updateEncoder() {
    int MSB = digitalRead(ENCODER_A);
    int LSB = digitalRead(ENCODER_B);
    int encoded = (MSB << 1) | LSB;
    int sum = (lastEncoded << 2) | encoded;

    if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011)
        encoderTicks--;
    if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000)
        encoderTicks++;

    lastEncoded = encoded;
}

void moveMotor(int pwm, int dir) {
    if (dir == 1) {
        digitalWrite(MOTOR_IN3, HIGH);
        digitalWrite(MOTOR_IN4, LOW);
    } else if (dir == -1) {
        digitalWrite(MOTOR_IN3, LOW);
        digitalWrite(MOTOR_IN4, HIGH);
    } else {
        digitalWrite(MOTOR_IN3, LOW);
        digitalWrite(MOTOR_IN4, LOW);
    }
    ledcWrite(PWM_CHANNEL, constrain(pwm, 0, 255));
}

float calculateRPM(long ticks, float sampleTimeMs) {
    if (sampleTimeMs <= 0 || speedConstant <= 0) return 0.0;
    float revolutions = (float)abs(ticks) / speedConstant;
    float rpm = revolutions / (sampleTimeMs / 60000.0);
    return rpm;
}

float computePID(float error, float dt) {
    if (controlMode == P_ONLY) {
        return Kp * error;
    } else if (controlMode == PI_CTRL) {
        integral += error * dt;
        integral = constrain(integral, -255, 255);
        return Kp * error + Ki * integral;
    } else if (controlMode == PD) {
        float derivative = (error - prevError) / dt;
        return Kp * error + Kd * derivative;
    } else {
        integral += error * dt;
        integral = constrain(integral, -255, 255);
        float derivative = (error - prevError) / dt;
        return Kp * error + Ki * integral + Kd * derivative;
    }
}

bool saveCalibration() {
    File file = LittleFS.open(CALIB_FILE, "w");
    if (!file) return false;
    file.write((uint8_t*)&speedConstant, sizeof(speedConstant));
    file.write((uint8_t*)&maxRPM, sizeof(maxRPM));
    file.close();
    return true;
}

void autoCalibrate() {
    Serial.println("CALIB_START");

    moveMotor(128, 1);
    delay(1000);

    noInterrupts();
    encoderTicks = 0;
    interrupts();

    delay(2000);

    noInterrupts();
    long ticks = encoderTicks;
    encoderTicks = 0;
    interrupts();

    moveMotor(0, 0);

    speedConstant = (float)abs(ticks) / 2.0;
    if (speedConstant < 1.0) speedConstant = 1.0;

    maxRPM = calculateRPM(ticks, 2000.0) * (255.0 / 128.0);

    saveCalibration();

    Serial.printf("CALIB_DONE,%.2f\n", speedConstant);
}

bool loadCalibration() {
    if (!LittleFS.exists(CALIB_FILE)) return false;
    File file = LittleFS.open(CALIB_FILE, "r");
    if (!file) return false;
    file.read((uint8_t*)&speedConstant, sizeof(speedConstant));
    if (file.available()) {
        file.read((uint8_t*)&maxRPM, sizeof(maxRPM));
    } else {
        maxRPM = 0;
    }
    file.close();
    return speedConstant > 1.0;
}

bool savePID() {
    File file = LittleFS.open(PID_FILE, "w");
    if (!file) return false;
    file.write((uint8_t*)&Kp, sizeof(Kp));
    file.write((uint8_t*)&Ki, sizeof(Ki));
    file.write((uint8_t*)&Kd, sizeof(Kd));
    file.write((uint8_t*)&controlMode, sizeof(controlMode));
    file.close();
    return true;
}

bool loadPID() {
    if (!LittleFS.exists(PID_FILE)) return false;
    File file = LittleFS.open(PID_FILE, "r");
    if (!file) return false;
    file.read((uint8_t*)&Kp, sizeof(Kp));
    file.read((uint8_t*)&Ki, sizeof(Ki));
    file.read((uint8_t*)&Kd, sizeof(Kd));
    file.read((uint8_t*)&controlMode, sizeof(controlMode));
    file.close();
    return true;
}

bool saveLinearRegion() {
    File file = LittleFS.open(LRC_FILE, "w");
    if (!file) return false;
    file.write((uint8_t*)&lrcMinPWM, sizeof(lrcMinPWM));
    file.write((uint8_t*)&lrcMaxPWM, sizeof(lrcMaxPWM));
    file.write((uint8_t*)&lrcMinRPM, sizeof(lrcMinRPM));
    file.write((uint8_t*)&lrcMaxRPM, sizeof(lrcMaxRPM));
    file.write((uint8_t*)&hasLinearRegion, sizeof(hasLinearRegion));
    file.close();
    return true;
}

bool loadLinearRegion() {
    if (!LittleFS.exists(LRC_FILE)) return false;
    File file = LittleFS.open(LRC_FILE, "r");
    if (!file) return false;
    size_t expectedSize = sizeof(lrcMinPWM) + sizeof(lrcMaxPWM) +
                          sizeof(lrcMinRPM) + sizeof(lrcMaxRPM) +
                          sizeof(hasLinearRegion);
    if (file.size() < (int)expectedSize) {
        file.close();
        return false;
    }
    file.read((uint8_t*)&lrcMinPWM, sizeof(lrcMinPWM));
    file.read((uint8_t*)&lrcMaxPWM, sizeof(lrcMaxPWM));
    file.read((uint8_t*)&lrcMinRPM, sizeof(lrcMinRPM));
    file.read((uint8_t*)&lrcMaxRPM, sizeof(lrcMaxRPM));
    file.read((uint8_t*)&hasLinearRegion, sizeof(hasLinearRegion));
    file.close();
    return true;
}

bool saveMotorChar() {
    File file = LittleFS.open(MCHAR_FILE, "w");
    if (!file) return false;
    file.write((uint8_t*)&charCount, sizeof(charCount));
    if (charCount > 0) {
        file.write((uint8_t*)charPWMValues, sizeof(int) * charCount);
        file.write((uint8_t*)charSpeedValues, sizeof(float) * charCount);
    }
    file.close();
    return true;
}

bool loadMotorChar() {
    if (!LittleFS.exists(MCHAR_FILE)) return false;
    File file = LittleFS.open(MCHAR_FILE, "r");
    if (!file) return false;
    file.read((uint8_t*)&charCount, sizeof(charCount));
    if (charCount < 0 || charCount > MAX_CHAR_POINTS) {
        charCount = 0;
        file.close();
        return false;
    }
    if (charCount > 0) {
        file.read((uint8_t*)charPWMValues, sizeof(int) * charCount);
        file.read((uint8_t*)charSpeedValues, sizeof(float) * charCount);
    }
    file.close();
    return charCount > 0;
}

void initFileSystem() {
    if (!LittleFS.begin(true)) {
        Serial.println("ERR,LITTLEFS_INIT_FAILED");
        return;
    }
    if (!LittleFS.exists("/")) {
        LittleFS.mkdir("/");
    }
}

void resetController() {
    integral = 0.0;
    prevError = 0.0;
    moveMotor(0, 0);
    runState = STATE_IDLE;
    Serial.println("ACK,RESET");
}

void printStatus() {
    Serial.println("ACK,STATUS");
    Serial.printf("SP,%.2f\n", setpoint);
    Serial.printf("SM,%d\n", samplingMs);
    Serial.printf("DUR,%d\n", durationMs);
    Serial.printf("KP,%.4f\n", Kp);
    Serial.printf("KI,%.4f\n", Ki);
    Serial.printf("KD,%.4f\n", Kd);
    Serial.printf("MODE,%s\n",
        controlMode == P_ONLY ? "P" :
        controlMode == PI_CTRL ? "PI" :
        controlMode == PD ? "PD" : "PID");
    Serial.printf("DIR,%d\n", direction);
    Serial.printf("SC,%.2f\n", speedConstant);
    Serial.printf("MX,%.2f\n", maxRPM);
}

int getInfoStatus() {
    bool hasCalib = (speedConstant > 1.0);
    bool hasChar = (charCount > 0) && hasLinearRegion;
    if (hasChar) return 2;
    if (hasCalib) return 1;
    return 0;
}

int calculateOpenLoopPWM(float targetRPM) {
    if (hasLinearRegion && (lrcMaxRPM - lrcMinRPM) > 0) {
        float pwm = lrcMinPWM + (targetRPM - lrcMinRPM) / (lrcMaxRPM - lrcMinRPM) * (lrcMaxPWM - lrcMinPWM);
        return constrain((int)pwm, 0, 255);
    }
    if (charCount > 1) {
        if (targetRPM <= charSpeedValues[0]) {
            return constrain(charPWMValues[0], 0, 255);
        }
        if (targetRPM >= charSpeedValues[charCount - 1]) {
            return constrain(charPWMValues[charCount - 1], 0, 255);
        }
        for (int i = 0; i < charCount - 1; i++) {
            if (targetRPM >= charSpeedValues[i] && targetRPM <= charSpeedValues[i + 1]) {
                float ratio = (targetRPM - charSpeedValues[i]) / (charSpeedValues[i + 1] - charSpeedValues[i]);
                return constrain((int)(charPWMValues[i] + ratio * (charPWMValues[i + 1] - charPWMValues[i])), 0, 255);
            }
        }
    }
    if (maxRPM > 0 && targetRPM <= maxRPM) {
        return constrain((int)(targetRPM / maxRPM * 255.0), 0, 255);
    }
    return 128;
}

void sendMotorInfo() {
    int status = getInfoStatus();
    Serial.println(status);

    if (status == 2) {
        Serial.printf("%.2f %.2f %.2f\n", lrcMinRPM, lrcMaxRPM, maxRPM);
    } else if (status == 1) {
        Serial.printf("%.2f\n", maxRPM);
    }

    for (int i = 0; i < charCount; i++) {
        Serial.printf("%d %.2f\n", charPWMValues[i], charSpeedValues[i]);
    }
}

void handleDataRequest() {
    switch (opMode) {
        case MODE_ENCODER: {
            noInterrupts();
            long ticks = encoderTicks;
            interrupts();
            Serial.println(ticks);
            break;
        }
        case MODE_SPEED_LOG:
            if (charCount > 0) {
                for (int i = 0; i < charCount; i++) {
                    Serial.printf("%d %.2f\n", charPWMValues[i], charSpeedValues[i]);
                }
            } else {
                Serial.println("0");
            }
            break;
        case MODE_OPEN_LOOP:
        case MODE_CLOSED_LOOP:
            sendMotorInfo();
            break;
        default:
            Serial.println(getInfoStatus());
            break;
    }
}

void startOpenLoop() {
    runState = STATE_RUNNING;
    integral = 0.0;
    prevError = 0.0;
    startTime = millis();
    lastSampleTime = startTime;

    openLoopPWM = calculateOpenLoopPWM(setpoint);
    moveMotor(openLoopPWM, direction);

    noInterrupts();
    encoderTicks = 0;
    interrupts();

    Serial.println("ACK,START");
}

void startClosedLoop() {
    runState = STATE_RUNNING;
    integral = 0.0;
    prevError = 0.0;
    startTime = millis();
    lastSampleTime = startTime;

    noInterrupts();
    encoderTicks = 0;
    interrupts();

    Serial.println("ACK,START");
}

void startSweep() {
    runState = STATE_SWEEP;
    sweepCurrentPWM = 0;
    charCount = 0;
    sweepStepStart = millis();

    moveMotor(sweepCurrentPWM, direction);

    noInterrupts();
    encoderTicks = 0;
    interrupts();

    Serial.println("0.00");
}

void parseCommand(String cmd) {
    cmd.trim();
    if (cmd.length() == 0) return;

    if (cmd.length() == 1) {
        char c = cmd.charAt(0);
        switch (c) {
            case 'o':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_OPEN_LOOP;
                Serial.println("ACK,MODE,OPEN_LOOP");
                return;
            case 'c':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_CLOSED_LOOP;
                Serial.println("ACK,MODE,CLOSED_LOOP");
                return;
            case 'e':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_ENCODER;
                Serial.println("ACK,MODE,ENCODER");
                return;
            case 's':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_SPEED_LOG;
                Serial.println("ACK,MODE,SPEED_LOG");
                return;
            case 'l':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_LINEAR_REGION;
                Serial.println("ACK,MODE,LINEAR_REGION");
                return;
            case '1':
                if (opMode == MODE_SPEED_LOG && runState == STATE_IDLE) {
                    startSweep();
                }
                return;
            case '2':
                handleDataRequest();
                return;
            case '4':
                moveMotor(0, 0);
                runState = STATE_IDLE;
                opMode = MODE_IDLE;
                integral = 0.0;
                prevError = 0.0;
                Serial.println("ACK,IDLE");
                return;
            default:
                break;
        }
    }

    if (cmd.startsWith("SETPOINT,")) {
        setpoint = cmd.substring(9).toFloat();
        Serial.printf("ACK,SETPOINT,%.2f\n", setpoint);
    }
    else if (cmd.startsWith("SAMPLING,")) {
        int val = cmd.substring(9).toInt();
        if (val >= 10 && val <= 1000) {
            samplingMs = val;
            Serial.printf("ACK,SAMPLING,%d\n", samplingMs);
        } else {
            Serial.println("ERR,SAMPLING_OUT_OF_RANGE [10-1000]");
        }
    }
    else if (cmd.startsWith("DURATION,")) {
        int val = cmd.substring(9).toInt();
        if (val > 0 && val <= MAX_DURATION) {
            durationMs = val;
            Serial.printf("ACK,DURATION,%d\n", durationMs);
        } else {
            Serial.printf("ERR,DURATION_OUT_OF_RANGE [1-%d]\n", MAX_DURATION);
        }
    }
    else if (cmd.startsWith("KP,")) {
        Kp = cmd.substring(3).toFloat();
        Serial.printf("ACK,KP,%.4f\n", Kp);
    }
    else if (cmd.startsWith("KI,")) {
        Ki = cmd.substring(3).toFloat();
        Serial.printf("ACK,KI,%.4f\n", Ki);
    }
    else if (cmd.startsWith("KD,")) {
        Kd = cmd.substring(3).toFloat();
        Serial.printf("ACK,KD,%.4f\n", Kd);
    }
    else if (cmd.startsWith("MODE,")) {
        String mode = cmd.substring(5);
        if (mode == "P") { controlMode = P_ONLY; Serial.println("ACK,MODE,P"); }
        else if (mode == "PI") { controlMode = PI_CTRL; Serial.println("ACK,MODE,PI"); }
        else if (mode == "PD") { controlMode = PD; Serial.println("ACK,MODE,PD"); }
        else if (mode == "PID") { controlMode = PID; Serial.println("ACK,MODE,PID"); }
        else { Serial.println("ERR,INVALID_MODE [P|PI|PD|PID]"); }
    }
    else if (cmd.startsWith("DIRECTION,")) {
        int val = cmd.substring(10).toInt();
        if (val == 1 || val == -1) {
            direction = val;
            Serial.printf("ACK,DIRECTION,%d\n", direction);
        } else {
            Serial.println("ERR,INVALID_DIRECTION [1|-1]");
        }
    }
    else if (cmd.startsWith("LRC_MIN_PWM,")) {
        lrcMinPWM = cmd.substring(12).toInt();
        Serial.printf("ACK,LRC_MIN_PWM,%d\n", lrcMinPWM);
    }
    else if (cmd.startsWith("LRC_MAX_PWM,")) {
        lrcMaxPWM = cmd.substring(12).toInt();
        Serial.printf("ACK,LRC_MAX_PWM,%d\n", lrcMaxPWM);
    }
    else if (cmd.startsWith("LRC_MIN_RPM,")) {
        lrcMinRPM = cmd.substring(12).toFloat();
        Serial.printf("ACK,LRC_MIN_RPM,%.2f\n", lrcMinRPM);
    }
    else if (cmd.startsWith("LRC_MAX_RPM,")) {
        lrcMaxRPM = cmd.substring(12).toFloat();
        Serial.printf("ACK,LRC_MAX_RPM,%.2f\n", lrcMaxRPM);
    }
    else if (cmd == "LRC_SAVE") {
        hasLinearRegion = true;
        saveLinearRegion();
        Serial.println("ACK,LRC_SAVE");
    }
    else if (cmd == "START") {
        if (runState != STATE_IDLE) {
            Serial.println("ERR,ALREADY_RUNNING");
            return;
        }
        if (opMode == MODE_OPEN_LOOP) {
            startOpenLoop();
        } else {
            if (opMode != MODE_CLOSED_LOOP) {
                opMode = MODE_CLOSED_LOOP;
            }
            startClosedLoop();
        }
    }
    else if (cmd == "STOP") {
        resetController();
        Serial.println("ACK,STOP");
    }
    else if (cmd == "RESET") {
        resetController();
    }
    else if (cmd == "STATUS") {
        printStatus();
    }
    else if (cmd == "SAVE") {
        savePID();
        Serial.println("ACK,SAVE");
    }
    else if (cmd == "LOAD") {
        if (loadPID()) {
            Serial.println("ACK,LOAD");
        } else {
            Serial.println("ERR,NO_SAVED_PID");
        }
    }
    else if (cmd == "CALIBRATE") {
        if (runState == STATE_IDLE) {
            autoCalibrate();
        } else {
            Serial.println("ERR,CALIBRATE_WHILE_RUNNING");
        }
    }
    else if (cmd == "HELP") {
        Serial.println("ACK,HELP");
        Serial.println("SETPOINT,<rpm>");
        Serial.println("SAMPLING,<ms> [10-1000]");
        Serial.println("DURATION,<ms> [1-15000]");
        Serial.println("KP,<val> | KI,<val> | KD,<val>");
        Serial.println("MODE,<P|PI|PD|PID>");
        Serial.println("DIRECTION,<1|-1>");
        Serial.println("START|STOP|RESET|STATUS|SAVE|LOAD|CALIBRATE|HELP");
        Serial.println("o|c|e|s|l - Mode (open|closed|encoder|speedlog|lrc)");
        Serial.println("1 - Start sweep | 2 - Request data | 4 - Idle");
        Serial.println("LRC_MIN_PWM,<v> | LRC_MAX_PWM,<v>");
        Serial.println("LRC_MIN_RPM,<v> | LRC_MAX_RPM,<v>");
        Serial.println("LRC_SAVE");
    }
    else {
        Serial.printf("ERR,UNKNOWN_COMMAND [%s]\n", cmd.c_str());
    }
}

void setup() {
    pinMode(ENCODER_A, INPUT_PULLUP);
    pinMode(ENCODER_B, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(ENCODER_A), updateEncoder, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_B), updateEncoder, CHANGE);

    pinMode(MOTOR_EN, OUTPUT);
    pinMode(MOTOR_IN3, OUTPUT);
    pinMode(MOTOR_IN4, OUTPUT);

    ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
    ledcAttachPin(MOTOR_EN, PWM_CHANNEL);
    ledcWrite(PWM_CHANNEL, 0);

    digitalWrite(MOTOR_IN3, HIGH);
    digitalWrite(MOTOR_IN4, LOW);

    Serial.begin(115200);
    delay(500);
    Serial.setTimeout(50);

    initFileSystem();

    loadLinearRegion();
    loadMotorChar();
    loadPID();

    Serial.printf("READY,%s\n", VERSION);

    autoCalibrate();
}

void loop() {
    while (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        parseCommand(cmd);
    }

    if (runState == STATE_SWEEP) {
        unsigned long now = millis();
        unsigned long settleElapsed = now - sweepStepStart;

        if (settleElapsed >= (unsigned long)SWEEP_SETTLE_MS) {
            noInterrupts();
            long ticks = encoderTicks;
            encoderTicks = 0;
            interrupts();

            float rpm = calculateRPM(ticks, (float)settleElapsed);

            if (charCount < MAX_CHAR_POINTS) {
                charPWMValues[charCount] = sweepCurrentPWM;
                charSpeedValues[charCount] = rpm;
                charCount++;
            }

            sweepCurrentPWM += SWEEP_STEP;

            if (sweepCurrentPWM > 255) {
                moveMotor(0, 0);
                runState = STATE_IDLE;

                float maxSpeed = 0;
                for (int i = 0; i < charCount; i++) {
                    if (charSpeedValues[i] > maxSpeed) maxSpeed = charSpeedValues[i];
                }
                if (maxSpeed > maxRPM) {
                    maxRPM = maxSpeed;
                    saveCalibration();
                }

                saveMotorChar();
                Serial.println("100.00");
                return;
            }

            moveMotor(sweepCurrentPWM, direction);
            sweepStepStart = millis();

            noInterrupts();
            encoderTicks = 0;
            interrupts();

            float progress = (float)sweepCurrentPWM / 255.0 * 100.0;
            Serial.printf("%.2f\n", progress);
        }
        return;
    }

    if (runState == STATE_RUNNING) {
        unsigned long now = millis();
        unsigned long elapsed = now - startTime;

        if (elapsed >= (unsigned long)durationMs) {
            moveMotor(0, 0);
            runState = STATE_IDLE;
            Serial.println("DONE");
            return;
        }

        if ((long)(now - lastSampleTime) >= samplingMs) {
            noInterrupts();
            long ticks = encoderTicks;
            encoderTicks = 0;
            interrupts();

            float dt = samplingMs / 1000.0;
            float rpm = calculateRPM(ticks, samplingMs);
            float error = setpoint - rpm;
            int pwm;

            if (opMode == MODE_OPEN_LOOP) {
                pwm = openLoopPWM;
            } else {
                float pidOutput = computePID(error, dt);
                pwm = (int)constrain(pidOutput, 0, 255);
                moveMotor(pwm, direction);
                prevError = error;
            }

            Serial.printf("DATA,%lu,%.2f,%.2f,%d\n", elapsed, rpm, error, pwm);

            lastSampleTime = now;
        }
    }
}
