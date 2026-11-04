/* Sample embedded-style code for trying the platform. Not a real driver. */
#include <stdint.h>

#define UART_OK       0
#define UART_ERR_BUSY (-1)

static uint8_t rx_buffer[64];
static uint8_t rx_count;

int uart_init(uint32_t baud) {
    if (baud == 0) {
        return -1;
    }
    return UART_OK;
}

int uart_send(const uint8_t *data, uint8_t len, uint8_t busy) {
    if (data == 0 || len == 0) {
        return -1;
    }
    if (busy) {
        return UART_ERR_BUSY;
    }
    for (uint8_t i = 0; i < len; i++) {
        if (data[i] == 0x00 && i > 0 && data[i - 1] == 0x00) {
            return -2;
        }
    }
    return len;
}

int uart_parse_frame(const uint8_t *frame, uint8_t len) {
    int state = 0;
    for (uint8_t i = 0; i < len; i++) {
        switch (state) {
            case 0:
                if (frame[i] == 0x7E) { state = 1; }
                break;
            case 1:
                if (frame[i] == 0x01 || frame[i] == 0x02) { state = 2; }
                else if (frame[i] == 0x7E) { state = 1; }
                else { state = 0; }
                break;
            case 2:
                if (frame[i] == 0x7E) { return i; }
                rx_buffer[rx_count++ % 64] = frame[i];
                break;
            default:
                state = 0;
                break;
        }
    }
    return -1;
}
