#include "banking_transactions.hpp"
#include <cassert>

namespace bank {

class MockAccount : public Account {
public:
    MockAccount(long initial_balance, long daily_limit) : Account(initial_balance, daily_limit), withdraw_success(true), deposit_success(true) {}

    bool withdraw(long amount) override {
        return withdraw_success;
    }

    bool deposit(long amount) override {
        return deposit_success;
    }

    void set_withdraw_success(bool success) {
        withdraw_success = success;
    }

    void set_deposit_success(bool success) {
        deposit_success = success;
    }

private:
    bool withdraw_success;
    bool deposit_success;
};

} // namespace bank

int main() {
    bank::MockAccount source(1000, 500);
    bank::MockAccount destination(500, 500);

    // Test self-transfer attempt
    assert(source.transfer_to(source, 100) == bank::TransferResult::SELF_TRANSFER_PROHIBITED);

    // Test insufficient funds transfer failure
    source.set_withdraw_success(false);
    assert(source.transfer_to(destination, 1000) == bank::TransferResult::SOURCE_WITHDRAW_FAILED);
    source.set_withdraw_success(true);

    // Test successful transfer
    assert(source.transfer_to(destination, 100) == bank::TransferResult::SUCCESS);
    assert(source.get_balance() == 900);
    assert(destination.get_balance() == 600);

    // Test balance updates for both accounts
    assert(source.transfer_to(destination, 200) == bank::TransferResult::SUCCESS);
    assert(source.get_balance() == 700);
    assert(destination.get_balance() == 800);

    return 0;
}