#ifndef BANKING_TRANSACTIONS_HPP
#define BANKING_TRANSACTIONS_HPP

#include <string>
#include <vector>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>

namespace bank {

enum class WithdrawResult {
    SUCCESS = 0,
    INVALID_AMOUNT,
    INSUFFICIENT_FUNDS,
    DAILY_LIMIT_EXCEEDED
};

enum class DepositResult {
    SUCCESS = 0,
    INVALID_AMOUNT,
    OVERFLOW_ERROR
};

enum class TransferResult {
    SUCCESS = 0,
    SELF_TRANSFER_PROHIBITED,
    SOURCE_WITHDRAW_FAILED,
    DESTINATION_CREDIT_FAILED
};

enum class AccountType {
    STANDARD = 0,
    PREMIUM,
    STUDENT,
    BUSINESS
};

enum class AuthStatus {
    AUTHENTICATED = 0,
    INVALID_CREDENTIALS,
    ACCOUNT_LOCKED,
    INVALID_INPUT
};

struct Transaction {
    std::string tx_id;
    long amount;
    std::string timestamp;
    std::string type;
};

struct TransactionRecord {
    std::string tx_id;
    long amount;
    uint32_t prev_hash;
    uint32_t hash;
};

/* 1, 2, 3: Account Class */
class Account {
public:
    Account(long initial_balance, long daily_limit);

    WithdrawResult withdraw(long amount);
    DepositResult deposit(long amount);
    TransferResult transfer_to(Account &destination, long amount);

    long get_balance() const;
    long get_daily_withdrawn() const;
    long get_daily_limit() const;
    void reset_daily_limit();

private:
    long balance_;
    long daily_limit_;
    long daily_withdrawn_;
};

/* 4: Interest Calculator */
class InterestCalculator {
public:
    static double calculate_accrued(double principal, double annual_rate, int days);
};

/* 5: Transaction Logger */
class TransactionLogger {
public:
    explicit TransactionLogger(size_t max_capacity = 100);
    bool log_transaction(const Transaction &tx);
    size_t count() const;
    void clear();

private:
    size_t max_capacity_;
    std::vector<Transaction> logs_;
};

/* 6: Security Manager */
class SecurityManager {
public:
    static const int MAX_ATTEMPTS = 3;
    static AuthStatus authenticate(const std::string &username,
                                   const std::string &provided_hash,
                                   const std::string &stored_hash,
                                   int current_attempts);
};

/* 7: Session Token */
class SessionToken {
public:
    SessionToken(uint64_t issued_at, uint64_t timeout_seconds);
    bool is_valid(uint64_t current_timestamp) const;
    void revoke();
    bool is_revoked() const;

private:
    uint64_t issued_at_;
    uint64_t timeout_seconds_;
    bool revoked_;
};

/* 8: Currency Converter */
class CurrencyConverter {
public:
    CurrencyConverter();
    void set_rate(const std::string &from_curr, const std::string &to_curr, double rate);
    long convert(long amount_cents, const std::string &from_curr, const std::string &to_curr) const;

private:
    std::unordered_map<std::string, double> rates_;
};

/* 9: Fee Schedule */
class FeeSchedule {
public:
    static long calculate_fee(long amount_cents, AccountType type, int monthly_tx_count);
};

/* 10: Audit Trail */
class AuditTrail {
public:
    static uint32_t compute_hash(const std::string &tx_id, long amount, uint32_t prev_hash);
    static bool verify_integrity(const std::vector<TransactionRecord> &records);
};

} // namespace bank

#endif // BANKING_TRANSACTIONS_HPP
