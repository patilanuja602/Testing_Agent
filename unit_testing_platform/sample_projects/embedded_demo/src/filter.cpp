// Sample C++ code for trying the platform.
#include <vector>

class MovingAverage {
public:
    explicit MovingAverage(int window) : window_(window > 0 ? window : 1) {}

    double push(double value) {
        samples_.push_back(value);
        if (static_cast<int>(samples_.size()) > window_) {
            samples_.erase(samples_.begin());
        }
        double sum = 0.0;
        for (double s : samples_) {
            sum += s;
        }
        return sum / samples_.size();
    }

private:
    int window_;
    std::vector<double> samples_;
};

int clamp(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
