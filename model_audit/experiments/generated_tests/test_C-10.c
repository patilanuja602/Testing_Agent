#include "sensor_monitoring.h"
#include <assert.h>
#include <stdio.h>

int main() {
    // Test emergency stop from running
    assert(sensor_fsm_step(FSM_RUNNING, CMD_EMERGENCY_STOP, 100.0f, 100.0f, false) == FSM_FAULT_LATCHED);
    assert(sensor_fsm_step(FSM_RUNNING, CMD_EMERGENCY_STOP, 50.0f, 50.0f, false) == FSM_FAULT_LATCHED);

    // Test hardware fault override from standby
    assert(sensor_fsm_step(FSM_STANDBY, CMD_START, 0.0f, 0.0f, true) == FSM_FAULT_LATCHED);
    assert(sensor_fsm_step(FSM_STANDBY, CMD_START, 0.0f, 0.0f, false) == FSM_ACCELERATING);

    // Test normal lifecycle (STANDBY -> START -> ACCELERATING -> target reached -> RUNNING -> STOP -> BRAKING -> stopped -> STANDBY)
    assert(sensor_fsm_step(FSM_STANDBY, CMD_START, 0.0f, 100.0f, false) == FSM_ACCELERATING);
    assert(sensor_fsm_step(FSM_ACCELERATING, CMD_NONE, 100.0f, 100.0f, false) == FSM_ACCELERATING);
    assert(sensor_fsm_step(FSM_ACCELERATING, CMD_NONE, 150.0f, 100.0f, false) == FSM_RUNNING);
    assert(sensor_fsm_step(FSM_RUNNING, CMD_STOP, 100.0f, 100.0f, false) == FSM_BRAKING);
    assert(sensor_fsm_step(FSM_BRAKING, CMD_NONE, 0.0f, 0.0f, false) == FSM_STANDBY);

    // Test fault recovery (FAULT_LATCHED + CMD_RESET without fault -> STANDBY)
    assert(sensor_fsm_step(FSM_FAULT_LATCHED, CMD_RESET, 0.0f, 0.0f, false) == FSM_STANDBY);

    // Test fault recovery blocked if hardware_fault still true
    assert(sensor_fsm_step(FSM_FAULT_LATCHED, CMD_RESET, 0.0f, 0.0f, true) == FSM_FAULT_LATCHED);

    printf("All tests passed!\n");
    return 0;
}