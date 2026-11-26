#include "sensor_monitoring.h"
#include <assert.h>
#include <stdio.h>

int main() {
    // Test assertions for sensor_raw_valid function
    assert(sensor_raw_valid(0) == true); // Minimum valid value
    assert(sensor_raw_valid(4095) == true); // Maximum valid value
    assert(sensor_raw_valid(-1) == false); // Below minimum value
    assert(sensor_raw_valid(4096) == false); // Above maximum value
    assert(sensor_raw_valid(2048) == true); // Normal nominal value
    assert(sensor_raw_valid(1000) == true); // Normal nominal value
    assert(sensor_raw_valid(3000) == true); // Normal nominal value

    printf("All tests passed successfully.\n");
    return 0;
}