#include "sensor_monitoring.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

#define EPSILON 0.001f

int main() {
    float temp_c;

    // Test case: NULL pointer error
    assert(sensor_scale_temperature(1000, NULL) == SENSOR_ERR_NULL_PTR);

    // Test case: out-of-range ADC below 0
    assert(sensor_scale_temperature(-100, &temp_c) == SENSOR_ERR_OUT_OF_RANGE);
    assert(fabsf(temp_c + 999.0f) < EPSILON);

    // Test case: out-of-range ADC above 4095
    assert(sensor_scale_temperature(5000, &temp_c) == SENSOR_ERR_OUT_OF_RANGE);
    assert(fabsf(temp_c + 999.0f) < EPSILON);

    // Test case: boundary at 0 (result -40.0 C)
    assert(sensor_scale_temperature(0, &temp_c) == SENSOR_OK);
    assert(fabsf(temp_c + 40.0f) < EPSILON);

    // Test case: boundary at 4095
    assert(sensor_scale_temperature(4095, &temp_c) == SENSOR_OK);
    assert(fabsf(temp_c - 0.0f) < EPSILON);

    // Test case: nominal mid-value
    assert(sensor_scale_temperature(2048, &temp_c) == SENSOR_OK);
    assert(fabsf(temp_c - 24.0f) < EPSILON);

    printf("All tests passed!\n");
    return 0;
}