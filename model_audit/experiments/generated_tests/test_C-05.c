#include "sensor_monitoring.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main() {
    // Test cases
    assert(sensor_can_frame_validate(0x2EF, 8, 0, 0) == SENSOR_ERR_OUT_OF_RANGE);
    assert(sensor_can_frame_validate(0x2F8, 8, 0, 0) == SENSOR_ERR_OUT_OF_RANGE);
    assert(sensor_can_frame_validate(0x2F0, 8, 0, 0) == SENSOR_OK);
    assert(sensor_can_frame_validate(0x2F7, 8, 0, 0) == SENSOR_OK);
    assert(sensor_can_frame_validate(0x2F0, 7, 0, 0) == SENSOR_ERR_INVALID_DLC);
    assert(sensor_can_frame_validate(0x2F0, 9, 0, 0) == SENSOR_ERR_INVALID_DLC);
    assert(sensor_can_frame_validate(0x2F0, 8, 0, 0) == SENSOR_OK);
    assert(sensor_can_frame_validate(0x2F0, 8, 1, 0) == SENSOR_OK);
    assert(sensor_can_frame_validate(0x2F0, 8, 0, 15) == SENSOR_OK);
    assert(sensor_can_frame_validate(0x2F0, 8, 4, 2) == SENSOR_ERR_COUNTER_SEQUENCE);

    printf("All tests passed successfully.\n");
    return 0;
}