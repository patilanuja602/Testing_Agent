#include "sensor_monitoring.h"
#include <assert.h>
#include <stdio.h>

int main() {
    // Test cases for underpressure
    assert(sensor_pressure_window_check(9.9f) == PRESSURE_FAULT_UNDERPRESSURE);
    assert(sensor_pressure_window_check(0.0f) == PRESSURE_FAULT_UNDERPRESSURE);
    assert(sensor_pressure_window_check(-5.0f) == PRESSURE_FAULT_UNDERPRESSURE);

    // Test case for lower boundary
    assert(sensor_pressure_window_check(10.0f) == PRESSURE_OK);

    // Test case for nominal mid-point
    assert(sensor_pressure_window_check(50.0f) == PRESSURE_OK);

    // Test case for upper boundary
    assert(sensor_pressure_window_check(150.0f) == PRESSURE_OK);

    // Test cases for overpressure
    assert(sensor_pressure_window_check(150.1f) == PRESSURE_FAULT_OVERPRESSURE);
    assert(sensor_pressure_window_check(200.0f) == PRESSURE_FAULT_OVERPRESSURE);

    printf("All tests passed successfully.\n");
    return 0;
}