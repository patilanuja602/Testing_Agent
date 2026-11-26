#ifndef SENSOR_MONITORING_H
#define SENSOR_MONITORING_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Constants */
#define SENSOR_RAW_MIN 0
#define SENSOR_RAW_MAX 4095

#define SENSOR_OK                     0
#define SENSOR_ERR_NULL_PTR         (-1)
#define SENSOR_ERR_OUT_OF_RANGE     (-2)
#define SENSOR_ERR_INVALID_DLC      (-3)
#define SENSOR_ERR_COUNTER_SEQUENCE (-4)
#define SENSOR_ERR_CRC_MISMATCH     (-5)
#define SENSOR_ERR_BUFFER_FULL      (-6)
#define SENSOR_ERR_EMPTY_TABLE      (-7)

/* Pressure states */
typedef enum {
    PRESSURE_OK = 0,
    PRESSURE_FAULT_UNDERPRESSURE = 1,
    PRESSURE_FAULT_OVERPRESSURE = 2
} PressureStatus;

/* Motor conveyor state machine */
typedef enum {
    FSM_STANDBY = 0,
    FSM_ACCELERATING = 1,
    FSM_RUNNING = 2,
    FSM_BRAKING = 3,
    FSM_FAULT_LATCHED = 4
} ConveyorState;

typedef enum {
    CMD_NONE = 0,
    CMD_START = 1,
    CMD_STOP = 2,
    CMD_EMERGENCY_STOP = 3,
    CMD_RESET = 4
} MotorCommand;

/* Circular buffer */
#define SENSOR_BUF_CAPACITY 8
typedef struct {
    uint32_t data[SENSOR_BUF_CAPACITY];
    size_t head;
    size_t count;
} SensorCircularBuffer;

/* Calibration point */
typedef struct {
    float raw;
    float calibrated;
} CalibrationPoint;

/* Functions under audit */

/* 1. sensor_raw_valid */
bool sensor_raw_valid(int raw_adc);

/* 2. sensor_scale_temperature */
int sensor_scale_temperature(int raw_adc, float *temp_c);

/* 3. sensor_battery_soc_eval */
int sensor_battery_soc_eval(float soc_percent, bool *low_battery_warning);

/* 4. sensor_pressure_window_check */
PressureStatus sensor_pressure_window_check(float pressure_bar);

/* 5. sensor_can_frame_validate */
int sensor_can_frame_validate(uint16_t id, uint8_t dlc, uint8_t counter, uint8_t last_counter);

/* 6. sensor_uart_crc16_verify */
int sensor_uart_crc16_verify(const uint8_t *payload, uint8_t len, uint16_t expected_crc);

/* 7. sensor_transient_error_filter */
int sensor_transient_error_filter(int error_occurred, int *consecutive_errors, int *status_offline);

/* 8. sensor_circular_buffer_push */
int sensor_circular_buffer_push(SensorCircularBuffer *buf, uint32_t sample);

/* 9. sensor_calibration_lookup */
int sensor_calibration_lookup(float raw_val, const CalibrationPoint *table, size_t table_size, float *calibrated_out);

/* 10. sensor_fsm_step */
ConveyorState sensor_fsm_step(ConveyorState current_state, MotorCommand cmd, float current_rpm, float target_rpm, bool hardware_fault);

#ifdef __cplusplus
}
#endif

#endif /* SENSOR_MONITORING_H */
