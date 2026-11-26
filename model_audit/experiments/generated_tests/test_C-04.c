#include "sensor_monitoring.h"
#include <assert.h>
#include <stdio.h>

int main() {
    // Test underpressure conditions
    assert(sensor_pressure_window_check(9.9f) == PRESSURE_FAULT_UNDERPRESSURE);
    assert(sensor_pressure_window_check(0.0f) == PRESSURE_FAULT_UNDERPRESSURE);
    assert(sensor_pressure_window_check(-5.0f) == PRESSURE_FAULT_UNDERPRESSURE);

    // Test lower boundary condition
    assert(sensor_pressure_window_check(10.0f) == PRESSURE_OK);

    // Test nominal mid-point condition
    assert(sensor_pressure_window_check(50.0f) == PRESSURE_OK);

    // Test upper boundary condition
    assert(sensor_pressure_window_check(150.0f) == PRESSURE_OK);

    // Test overpressure conditions
    assert(sensor_pressure_window_check(150.1f) == PRESSURE_FAULT_OVERPRESSURE);
    assert(sensor_pressure_window_check(200.0f) == PRESSURE_FAULT_OVERPRESSURE);

    printf("All tests passed successfully.\n");
    return 0;
}