#include "sensor_monitoring.h"
#include <assert.h>
#include <stdio.h>

int main() {
    int error_occurred = 0;
    int consecutive_errors = 0;
    int status_offline = 0;

    // Test case 1: NULL consecutive_errors pointer
    error_occurred = 1;
    consecutive_errors = 0;
    status_offline = 0;
    assert(sensor_transient_error_filter(error_occurred, NULL, &status_offline) == SENSOR_ERR_NULL_PTR);

    // Test case 2: NULL status_offline pointer
    error_occurred = 1;
    consecutive_errors = 0;
    status_offline = 0;
    assert(sensor_transient_error_filter(error_occurred, &consecutive_errors, NULL) == SENSOR_ERR_NULL_PTR);

    // Test case 3: Single transient error (counter becomes 1, offline remains 0)
    error_occurred = 1;
    consecutive_errors = 0;
    status_offline = 0;
    assert(sensor_transient_error_filter(error_occurred, &consecutive_errors, &status_offline) == SENSOR_OK);
    assert(consecutive_errors == 1);
    assert(status_offline == 0);

    // Test case 4: Recovery on error=0 (counter resets to 0, offline remains 0)
    error_occurred = 0;
    consecutive_errors = 1;
    status_offline = 0;
    assert(sensor_transient_error_filter(error_occurred, &consecutive_errors, &status_offline) == SENSOR_OK);
    assert(consecutive_errors == 0);
    assert(status_offline == 0);

    // Test case 5: 3 consecutive errors triggering offline latch (*consecutive_errors=3, *status_offline=1)
    error_occurred = 1;
    consecutive_errors = 2;
    status_offline = 0;
    assert(sensor_transient_error_filter(error_occurred, &consecutive_errors, &status_offline) == SENSOR_OK);
    assert(consecutive_errors == 3);
    assert(status_offline == 1);

    // Test case 6: Fourth consecutive error (*consecutive_errors=4, *status_offline=1)
    error_occurred = 1;
    consecutive_errors = 3;
    status_offline = 1;
    assert(sensor_transient_error_filter(error_occurred, &consecutive_errors, &status_offline) == SENSOR_OK);
    assert(consecutive_errors == 4);
    assert(status_offline == 1);

    printf("All tests passed successfully.\n");
    return 0;
}