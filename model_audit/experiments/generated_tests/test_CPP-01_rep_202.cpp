#include "banking_transactions.hpp"
#include <cassert>

int main() {
    // Test default constructor and initial state
    bank::Account acc(1000, 500);
    assert(acc.get_balance() == 1000);
    assert(acc.get_daily_withdrawn() == 0);
    assert(acc.get_daily_limit() == 500);

    // Test withdraw with invalid amount
    assert(acc.withdraw(0) == bank::WithdrawResult::INVALID_AMOUNT);
    assert(acc.withdraw(-100) == bank::WithdrawResult::INVALID_AMOUNT);

    // Test withdraw with insufficient funds
    assert(acc.withdraw(1500) == bank::WithdrawResult::INSUFFICIENT_FUNDS);

    // Test withdraw with daily limit exceeded
    assert(acc.withdraw(300) == bank::WithdrawResult::SUCCESS);
    assert(acc.withdraw(300) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);

    // Test reset daily limit
    acc.reset_daily_limit();
    assert(acc.withdraw(300) == bank::WithdrawResult::SUCCESS);

    // Test multiple successful withdrawals
    assert(acc.withdraw(200) == bank::WithdrawResult::SUCCESS);
    assert(acc.withdraw(100) == bank::WithdrawResult::SUCCESS);
    assert(acc.get_balance() == 500);
    assert(acc.get_daily_withdrawn() == 600);

    // Test reset daily limit after multiple withdrawals
    acc.reset_daily_limit();
    assert(acc.withdraw(300) == bank::WithdrawResult::SUCCESS);

    // Test withdraw with exactly daily limit
    assert(acc.withdraw(200) == bank::WithdrawResult::SUCCESS);
    assert(acc.withdraw(100) == bank::WithdrawResult::SUCCESS);
    assert(acc.withdraw(100) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);

    // Test reset daily limit after reaching daily limit
    acc.reset_daily_limit();
    assert(acc.withdraw(300) == bank::WithdrawResult::SUCCESS);

    // Test withdraw with zero daily limit
    bank::Account acc_zero_limit(1000, 0);
    assert(acc_zero_limit.withdraw(100) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);

    // Test reset daily limit with zero daily limit
    acc_zero_limit.reset_daily_limit();
    assert(acc_zero_limit.withdraw(100) == bank::WithdrawResult::SUCCESS);

    return 0;
}