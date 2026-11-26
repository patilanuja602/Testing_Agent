#include "banking_transactions.hpp"
#include <climits>
#include <cmath>

namespace bank {

Account::Account(long initial_balance, long daily_limit)
    : balance_(initial_balance), daily_limit_(daily_limit), daily_withdrawn_(0) {}

WithdrawResult Account::withdraw(long amount) {
    if (amount <= 0) {
        return WithdrawResult::INVALID_AMOUNT;
    }
    if (amount > balance_) {
        return WithdrawResult::INSUFFICIENT_FUNDS;
    }
    if (daily_withdrawn_ + amount > daily_limit_) {
        return WithdrawResult::DAILY_LIMIT_EXCEEDED;
    }
    balance_ -= amount;
    daily_withdrawn_ += amount;
    return WithdrawResult::SUCCESS;
}

DepositResult Account::deposit(long amount) {
    if (amount <= 0) {
        return DepositResult::INVALID_AMOUNT;
    }
    if (LONG_MAX - amount < balance_) {
        return DepositResult::OVERFLOW_ERROR;
    }
    balance_ += amount;
    return DepositResult::SUCCESS;
}

TransferResult Account::transfer_to(Account &destination, long amount) {
    if (this == &destination) {
        return TransferResult::SELF_TRANSFER_PROHIBITED;
    }
    WithdrawResult w_res = withdraw(amount);
    if (w_res != WithdrawResult::SUCCESS) {
        return TransferResult::SOURCE_WITHDRAW_FAILED;
    }
    DepositResult d_res = destination.deposit(amount);
    if (d_res != DepositResult::SUCCESS) {
        // Rollback source account withdrawal to preserve atomicity invariant
        deposit(amount);
        return TransferResult::DESTINATION_CREDIT_FAILED;
    }
    return TransferResult::SUCCESS;
}

long Account::get_balance() const { return balance_; }
long Account::get_daily_withdrawn() const { return daily_withdrawn_; }
long Account::get_daily_limit() const { return daily_limit_; }
void Account::reset_daily_limit() { daily_withdrawn_ = 0; }

double InterestCalculator::calculate_accrued(double principal, double annual_rate, int days) {
    if (principal < 0.0 || annual_rate < 0.0 || days < 0) {
        return -1.0;
    }
    // Simple daily interest accrual using 365-day convention
    double daily_rate = annual_rate / 365.0;
    return principal * daily_rate * static_cast<double>(days);
}

TransactionLogger::TransactionLogger(size_t max_capacity) : max_capacity_(max_capacity) {}

bool TransactionLogger::log_transaction(const Transaction &tx) {
    if (tx.tx_id.empty() || tx.amount == 0) {
        return false;
    }
    if (logs_.size() >= max_capacity_) {
        logs_.erase(logs_.begin());
    }
    logs_.push_back(tx);
    return true;
}

size_t TransactionLogger::count() const { return logs_.size(); }
void TransactionLogger::clear() { logs_.clear(); }

AuthStatus SecurityManager::authenticate(const std::string &username,
                                         const std::string &provided_hash,
                                         const std::string &stored_hash,
                                         int current_attempts) {
    if (username.empty() || provided_hash.empty()) {
        return AuthStatus::INVALID_INPUT;
    }
    if (current_attempts >= MAX_ATTEMPTS) {
        return AuthStatus::ACCOUNT_LOCKED;
    }
    if (provided_hash == stored_hash) {
        return AuthStatus::AUTHENTICATED;
    }
    return AuthStatus::INVALID_CREDENTIALS;
}

SessionToken::SessionToken(uint64_t issued_at, uint64_t timeout_seconds)
    : issued_at_(issued_at), timeout_seconds_(timeout_seconds), revoked_(false) {}

bool SessionToken::is_valid(uint64_t current_timestamp) const {
    if (revoked_) {
        return false;
    }
    if (current_timestamp < issued_at_) {
        return false; // Time travel / clock skew invalid
    }
    return (current_timestamp - issued_at_) <= timeout_seconds_;
}

void SessionToken::revoke() { revoked_ = true; }
bool SessionToken::is_revoked() const { return revoked_; }

CurrencyConverter::CurrencyConverter() {
    rates_["USD_EUR"] = 0.92;
    rates_["EUR_USD"] = 1.087;
    rates_["USD_GBP"] = 0.79;
    rates_["GBP_USD"] = 1.265;
}

void CurrencyConverter::set_rate(const std::string &from_curr, const std::string &to_curr, double rate) {
    rates_[from_curr + "_" + to_curr] = rate;
}

long CurrencyConverter::convert(long amount_cents, const std::string &from_curr, const std::string &to_curr) const {
    if (amount_cents <= 0) {
        return 0;
    }
    if (from_curr == to_curr) {
        return amount_cents;
    }
    std::string key = from_curr + "_" + to_curr;
    auto it = rates_.find(key);
    if (it == rates_.end()) {
        throw std::invalid_argument("Unsupported currency pair: " + key);
    }
    return static_cast<long>(std::round(static_cast<double>(amount_cents) * it->second));
}

long FeeSchedule::calculate_fee(long amount_cents, AccountType type, int monthly_tx_count) {
    if (amount_cents <= 0) {
        return 0;
    }
    if (monthly_tx_count <= 5) {
        return 0; // First 5 transactions free per month
    }
    switch (type) {
        case AccountType::PREMIUM:
            return 10; // Flat 10 cents
        case AccountType::STUDENT:
            return 5;  // Flat 5 cents
        case AccountType::BUSINESS:
            return static_cast<long>(amount_cents * 0.005); // 0.5%
        case AccountType::STANDARD:
        default:
            return static_cast<long>(amount_cents * 0.01);  // 1.0%
    }
}

uint32_t AuditTrail::compute_hash(const std::string &tx_id, long amount, uint32_t prev_hash) {
    uint32_t h = prev_hash ^ 0x9e3779b9;
    for (char c : tx_id) {
        h = (h << 5) + h + static_cast<uint8_t>(c);
    }
    h ^= static_cast<uint32_t>(amount);
    return h;
}

bool AuditTrail::verify_integrity(const std::vector<TransactionRecord> &records) {
    if (records.empty()) {
        return true;
    }
    uint32_t expected_prev = 0;
    for (const auto &rec : records) {
        if (rec.prev_hash != expected_prev) {
            return false;
        }
        uint32_t calculated = compute_hash(rec.tx_id, rec.amount, rec.prev_hash);
        if (calculated != rec.hash) {
            return false;
        }
        expected_prev = rec.hash;
    }
    return true;
}

} // namespace bank
