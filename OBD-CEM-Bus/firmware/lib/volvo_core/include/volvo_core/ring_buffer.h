#pragma once

#include <cstddef>
#include <cstdint>

namespace volvo {

// Einfacher Ringpuffer ohne dynamische Allokation.
// Ist der Puffer voll, wird der aelteste Eintrag ueberschrieben und
// verworfen gezaehlt. Nicht thread-safe; der Aufrufer muss synchronisieren.
template <typename T, size_t N>
class RingBuffer {
 public:
  static_assert(N > 0, "Ringpuffer braucht mindestens einen Platz");

  bool push(const T& value) {
    bool dropped = false;
    if (count_ == N) {
      dropped = true;
      ++dropped_;
      start_ = (start_ + 1) % N;
      --count_;
    }
    data_[(start_ + count_) % N] = value;
    ++count_;
    return !dropped;
  }

  void clear() {
    start_ = 0;
    count_ = 0;
    dropped_ = 0;
  }

  size_t size() const { return count_; }
  size_t capacity() const { return N; }
  uint32_t dropped() const { return dropped_; }
  bool empty() const { return count_ == 0; }
  bool full() const { return count_ == N; }

  const T& at(size_t index) const { return data_[(start_ + index) % N]; }

  // Kopiert die aeltesten bis neuesten Eintraege in destination.
  // Rueckgabe: Anzahl kopierter Eintraege.
  size_t copyTo(T* destination, size_t max_count) const {
    size_t n = count_ < max_count ? count_ : max_count;
    for (size_t i = 0; i < n; ++i) destination[i] = at(i);
    return n;
  }

 private:
  T data_[N] = {};
  size_t start_ = 0;
  size_t count_ = 0;
  uint32_t dropped_ = 0;
};

}  // namespace volvo
