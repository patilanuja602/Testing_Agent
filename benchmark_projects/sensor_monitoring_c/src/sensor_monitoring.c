#include "sensor_monitoring.h"

/* 1. sensor_raw_valid: validates raw 12-bit ADC range [0, 4095] */
bool sensor_raw_valid(int raw_adc) {
    if (raw_adc < SENSOR_RAW_MIN) {
        return false;
    }
    if (raw_adc > SENSOR_RAW_MAX) {
        return false;
    }
    return true;
}

/* 2. sensor_scale_temperature: Linear scaling Temperature_C = (raw_adc * 0.0805) - 40.0 */
int sensor_scale_temperature(int raw_adc, float *temp_c) {
    if (temp_c == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (!sensor_raw_valid(raw_adc)) {
        *temp_c = -999.0f;
        return SENSOR_ERR_OUT_OF_RANGE;
    }
    *temp_c = ((float)raw_adc * 0.0805f) - 40.0f;
    return SENSOR_OK;
}

/* 3. sensor_battery_soc_eval: SoC < 15.0% triggers warning, >= 15.0% clears warning */
int sensor_battery_soc_eval(float soc_percent, bool *low_battery_warning) {
    if (low_battery_warning == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (soc_percent < 0.0f || soc_percent > 100.0f) {
        return SENSOR_ERR_OUT_OF_RANGE;
    }
    if (soc_percent < 15.0f) {
        *low_battery_warning = true;
    } else {
        *low_battery_warning = false;
    }
    return SENSOR_OK;
}

/* 4. sensor_pressure_window_check: [10.0, 150.0] bar inclusive */
PressureStatus sensor_pressure_window_check(float pressure_bar) {
    if (pressure_bar < 10.0f) {
        return PRESSURE_FAULT_UNDERPRESSURE;
    }
    if (pressure_bar > 150.0f) {
        return PRESSURE_FAULT_OVERPRESSURE;
    }
    return PRESSURE_OK;
}

/* 5. sensor_can_frame_validate: ID in [0x2F0, 0x2F7], DLC==8, rolling counter modulo 16 */
int sensor_can_frame_validate(uint16_t id, uint8_t dlc, uint8_t counter, uint8_t last_counter) {
    if (id < 0x2F0 || id > 0x2F7) {
        return SENSOR_ERR_OUT_OF_RANGE;
    }
    if (dlc != 8) {
        return SENSOR_ERR_INVALID_DLC;
    }
    uint8_t expected = (last_counter + 1) & 0x0F;
    if (counter != expected) {
        return SENSOR_ERR_COUNTER_SEQUENCE;
    }
    return SENSOR_OK;
}

/* 6. sensor_uart_crc16_verify: CRC-16-CCITT (poly 0x1021, init 0xFFFF) */
int sensor_uart_crc16_verify(const uint8_t *payload, uint8_t len, uint16_t expected_crc) {
    if (payload == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (len == 0) {
        return SENSOR_ERR_OUT_OF_RANGE;
    }
    uint16_t crc = 0xFFFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= (uint16_t)payload[i] << 8;
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }
    if (crc != expected_crc) {
        return SENSOR_ERR_CRC_MISMATCH;
    }
    return SENSOR_OK;
}

/* 7. sensor_transient_error_filter: 3 consecutive errors triggers SENSOR_OFFLINE */
int sensor_transient_error_filter(int error_occurred, int *consecutive_errors, int *status_offline) {
    if (consecutive_errors == NULL || status_offline == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (error_occurred) {
        (*consecutive_errors)++;
        if (*consecutive_errors >= 3) {
            *status_offline = 1;
        }
    } else {
        *consecutive_errors = 0;
    }
    return SENSOR_OK;
}

/* 8. sensor_circular_buffer_push: pushes uint32 sample, returns error if full */
int sensor_circular_buffer_push(SensorCircularBuffer *buf, uint32_t sample) {
    if (buf == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (buf->count >= SENSOR_BUF_CAPACITY) {
        return SENSOR_ERR_BUFFER_FULL;
    }
    size_t write_idx = (buf->head + buf->count) % SENSOR_BUF_CAPACITY;
    buf->data[write_idx] = sample;
    buf->count++;
    return SENSOR_OK;
}

/* 9. sensor_calibration_lookup: linear interpolation from sorted table */
int sensor_calibration_lookup(float raw_val, const CalibrationPoint *table, size_t table_size, float *calibrated_out) {
    if (table == NULL || calibrated_out == NULL) {
        return SENSOR_ERR_NULL_PTR;
    }
    if (table_size == 0) {
        return SENSOR_ERR_EMPTY_TABLE;
    }
    if (raw_val <= table[0].raw) {
        *calibrated_out = table[0].calibrated;
        return SENSOR_OK;
    }
    if (raw_val >= table[table_size - 1].raw) {
        *calibrated_out = table[table_size - 1].calibrated;
        return SENSOR_OK;
    }
    for (size_t i = 0; i < table_size - 1; i++) {
        if (raw_val >= table[i].raw && raw_val <= table[i + 1].raw) {
            float span = table[i + 1].raw - table[i].raw;
            if (span == 0.0f) {
                *calibrated_out = table[i].calibrated;
            } else {
                float frac = (raw_val - table[i].raw) / span;
                *calibrated_out = table[i].calibrated + frac * (table[i + 1].calibrated - table[i].calibrated);
            }
            return SENSOR_OK;
        }
    }
    return SENSOR_ERR_OUT_OF_RANGE;
}

/* 10. sensor_fsm_step: Conveyor state machine transition logic */
ConveyorState sensor_fsm_step(ConveyorState current_state, MotorCommand cmd, float current_rpm, float target_rpm, bool hardware_fault) {
    if (hardware_fault || cmd == CMD_EMERGENCY_STOP) {
        return FSM_FAULT_LATCHED;
    }
    switch (current_state) {
        case FSM_STANDBY:
            if (cmd == CMD_START) {
                return FSM_ACCELERATING;
            }
            break;
        case FSM_ACCELERATING:
            if (current_rpm >= target_rpm && target_rpm > 0.0f) {
                return FSM_RUNNING;
            }
            if (cmd == CMD_STOP) {
                return FSM_BRAKING;
            }
            break;
        case FSM_RUNNING:
            if (cmd == CMD_STOP) {
                return FSM_BRAKING;
            }
            break;
        case FSM_BRAKING:
            if (current_rpm <= 0.0f) {
                return FSM_STANDBY;
            }
            break;
        case FSM_FAULT_LATCHED:
            if (cmd == CMD_RESET && !hardware_fault) {
                return FSM_STANDBY;
            }
            return FSM_FAULT_LATCHED;
        default:
            return FSM_STANDBY;
    }
    return current_state;
}
