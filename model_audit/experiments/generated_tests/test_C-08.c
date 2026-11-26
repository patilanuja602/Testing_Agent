#include "sensor_monitoring.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main() {
    SensorCircularBuffer buf;
    uint32_t sample = 42;

    // Test case: NULL buffer pointer
    assert(sensor_circular_buffer_push(NULL, sample) == SENSOR_ERR_NULL_PTR);

    // Test case: pushing into empty buffer (count becomes 1, sample stored)
    buf.head = 0;
    buf.count = 0;
    assert(sensor_circular_buffer_push(&buf, sample) == SENSOR_OK);
    assert(buf.count == 1);
    assert(buf.data[buf.head] == sample);

    // Test case: filling buffer to capacity (count becomes 8)
    for (size_t i = 1; i < SENSOR_BUF_CAPACITY; ++i) {
        assert(sensor_circular_buffer_push(&buf, i) == SENSOR_OK);
        assert(buf.count == i + 1);
        assert(buf.data[(buf.head + i) % SENSOR_BUF_CAPACITY] == i);
    }

    // Test case: pushing when buffer is full (returns SENSOR_ERR_BUFFER_FULL, count remains 8)
    assert(sensor_circular_buffer_push(&buf, 9) == SENSOR_ERR_BUFFER_FULL);
    assert(buf.count == SENSOR_BUF_CAPACITY);

    // Test case: wrapping when head is non-zero
    buf.head = 1;
    buf.count = SENSOR_BUF_CAPACITY;
    assert(sensor_circular_buffer_push(&buf, sample) == SENSOR_OK);
    assert(buf.count == SENSOR_BUF_CAPACITY + 1);
    assert(buf.data[(buf.head + SENSOR_BUF_CAPACITY) % SENSOR_BUF_CAPACITY] == sample);

    printf("All tests passed successfully.\n");
    return 0;
}