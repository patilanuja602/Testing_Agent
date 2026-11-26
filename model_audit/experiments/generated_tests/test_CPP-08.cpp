#include "banking_transactions.hpp"
#include <stdexcept>
#include <cassert>
#include <string>

int main() {
    bank::CurrencyConverter converter;
    
    // Test zero/negative amount
    assert(converter.convert(0, "USD", "EUR") == 0);
    assert(converter.convert(-100, "USD", "EUR") == 0);
    
    // Test identical currencies
    assert(converter.convert(1000, "USD", "USD") == 1000);
    assert(converter.convert(1000, "EUR", "EUR") == 1000);
    assert(converter.convert(1000, "GBP", "GBP") == 1000);
    
    // Test standard conversion (USD to EUR)
    assert(converter.convert(1000, "USD", "EUR") == static_cast<long>(std::round(1000 * 0.92)));
    
    // Test exception throwing for unsupported currency pair
    try {
        converter.convert(1000, "USD", "JPY");
        assert(false); // Should not reach here
    } catch (const std::invalid_argument &e) {
        // Expected exception
    }
    
    // Test setting and using custom rates
    converter.set_rate("USD", "JPY", 110.5);
    assert(converter.convert(1000, "USD", "JPY") == static_cast<long>(std::round(1000 * 110.5)));
    
    // Test setting and using custom rates in reverse
    converter.set_rate("JPY", "USD", 0.009045);
    assert(converter.convert(1000, "JPY", "USD") == static_cast<long>(std::round(1000 * 0.009045)));
    
    // Test setting and using custom rates with identical currencies
    converter.set_rate("USD", "USD", 1.0);
    assert(converter.convert(1000, "USD", "USD") == 1000);
    
    // Test setting and using custom rates with unknown currency pair
    try {
        converter.convert(1000, "USD", "XYZ");
        assert(false); // Should not reach here
    } catch (const std::invalid_argument &e) {
        // Expected exception
    }
    
    return 0;
}