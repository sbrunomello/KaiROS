#include <errno.h>
#include <signal.h>
#include <softPwm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <wiringPi.h>

#define SERVO_PIN 6
#define PWM_RANGE 200

#define SERVO_MIN_PWM 10
#define SERVO_MAX_PWM 20
#define SERVO_MIN_ANGLE 0
#define SERVO_MAX_ANGLE 180

#define TARGET_FILE "/tmp/kairos_servo_target"

static volatile sig_atomic_t keep_running = 1;

static float clamp_float(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static int angle_to_pwm(float angle) {
    angle = clamp_float(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
    float ratio = (angle - SERVO_MIN_ANGLE) / (float)(SERVO_MAX_ANGLE - SERVO_MIN_ANGLE);
    float pwm = SERVO_MIN_PWM + ratio * (SERVO_MAX_PWM - SERVO_MIN_PWM);
    return (int)(pwm + 0.5f);
}

static float read_target_angle(float fallback) {
    FILE *fp = fopen(TARGET_FILE, "r");
    if (!fp) return fallback;

    float angle = fallback;
    if (fscanf(fp, "%f", &angle) != 1) {
        fclose(fp);
        return fallback;
    }

    fclose(fp);
    return clamp_float(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
}

static void handle_signal(int sig) {
    (void)sig;
    keep_running = 0;
}

static void initialize_target_file(float angle) {
    FILE *fp = fopen(TARGET_FILE, "w");
    if (!fp) {
        fprintf(stderr, "[kairos-servo-daemon] falha ao abrir target file %s: %s\n", TARGET_FILE, strerror(errno));
        return;
    }

    fprintf(fp, "%.1f\n", angle);
    fclose(fp);

    if (chmod(TARGET_FILE, 0666) != 0) {
        fprintf(stderr, "[kairos-servo-daemon] aviso: chmod falhou em %s: %s\n", TARGET_FILE, strerror(errno));
    }
}

int main(void) {
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    if (wiringPiSetup() == -1) {
        fprintf(stderr, "[kairos-servo-daemon] erro ao iniciar wiringPi\n");
        return 1;
    }

    float current_angle = 90.0f;
    float target_angle = 90.0f;
    int current_pwm = angle_to_pwm(current_angle);

    if (softPwmCreate(SERVO_PIN, current_pwm, PWM_RANGE) != 0) {
        fprintf(stderr, "[kairos-servo-daemon] erro ao iniciar softPWM\n");
        return 1;
    }

    initialize_target_file(current_angle);

    printf("[kairos-servo-daemon] iniciado pin=%d angle=%.1f pwm=%d\n", SERVO_PIN, current_angle, current_pwm);
    fflush(stdout);

    while (keep_running) {
        target_angle = read_target_angle(target_angle);
        float delta = target_angle - current_angle;

        if (delta > 1.0f) delta = 1.0f;
        if (delta < -1.0f) delta = -1.0f;

        if (delta > 0.05f || delta < -0.05f) {
            current_angle = clamp_float(current_angle + delta, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
            current_pwm = angle_to_pwm(current_angle);
            softPwmWrite(SERVO_PIN, current_pwm);
        }

        delay(20);
    }

    softPwmWrite(SERVO_PIN, angle_to_pwm(90.0f));
    printf("[kairos-servo-daemon] finalizado com sucesso\n");
    return 0;
}
