#include "ant_engine/indicators.hpp"
#include <cmath>
#include <algorithm>

namespace ant_engine {

namespace {

constexpr double kEmaAlpha(int period) {
  return 2.0 / (period + 1);
}

}  // namespace

std::vector<double> ComputeEMA(const std::vector<Candle>& candles, int period) {
  std::vector<double> out;
  out.reserve(candles.size());
  if (candles.empty() || period < 1) return out;
  if (static_cast<size_t>(period) > candles.size()) return out;

  double sum = 0;
  for (int i = 0; i < period; ++i) sum += candles[i].c;
  double sma = sum / period;
  for (int i = 0; i < period; ++i) out.push_back(sma);

  double alpha = kEmaAlpha(period);
  double ema = alpha * candles[period].c + (1.0 - alpha) * sma;
  out.push_back(ema);
  for (size_t i = period + 1; i < candles.size(); ++i) {
    ema = alpha * candles[i].c + (1.0 - alpha) * ema;
    out.push_back(ema);
  }
  return out;
}

std::vector<double> ComputeRSI(const std::vector<Candle>& candles, int period) {
  std::vector<double> out;
  out.reserve(candles.size());
  if (candles.size() < 2 || period < 1) return out;

  out.push_back(50.0);
  double avg_gain = 0, avg_loss = 0;
  int gains = 0, losses = 0;
  for (int i = 1; i <= period && i < static_cast<int>(candles.size()); ++i) {
    double ch = candles[i].c - candles[i - 1].c;
    if (ch > 0) { avg_gain += ch; ++gains; }
    else if (ch < 0) { avg_loss += -ch; ++losses; }
  }
  if (period < static_cast<int>(candles.size())) {
    avg_gain /= period;
    avg_loss /= period;
  }
  for (int i = 1; i < period && i < static_cast<int>(candles.size()); ++i)
    out.push_back(50.0);

  for (size_t i = period; i < candles.size(); ++i) {
    double ch = candles[i].c - candles[i - 1].c;
    double g = (ch > 0) ? ch : 0.0;
    double l = (ch < 0) ? -ch : 0.0;
    avg_gain = (avg_gain * (period - 1) + g) / period;
    avg_loss = (avg_loss * (period - 1) + l) / period;
    double rs = (avg_loss <= 0) ? 100.0 : (avg_gain / avg_loss);
    double rsi = 100.0 - 100.0 / (1.0 + rs);
    out.push_back(rsi);
  }
  return out;
}

std::vector<double> ComputeADX(const std::vector<Candle>& candles, int period) {
  std::vector<double> out(candles.size(), 0.0);
  if (candles.size() < static_cast<size_t>(period + 1) || period < 1) return out;

  std::vector<double> tr(candles.size(), 0.0);
  std::vector<double> plus_dm(candles.size(), 0.0);
  std::vector<double> minus_dm(candles.size(), 0.0);

  for (size_t i = 1; i < candles.size(); ++i) {
    double high = candles[i].h, low = candles[i].l;
    double prev_high = candles[i - 1].h, prev_low = candles[i - 1].l;
    double prev_close = candles[i - 1].c;
    tr[i] = std::max({ high - low, std::abs(high - prev_close), std::abs(low - prev_close) });
    double up = high - prev_high;
    double down = prev_low - low;
    if (up > down && up > 0) plus_dm[i] = up;
    if (down > up && down > 0) minus_dm[i] = down;
  }

  double atr = 0, smooth_plus = 0, smooth_minus = 0;
  for (int i = 1; i <= period && i < static_cast<int>(candles.size()); ++i) {
    atr += tr[i];
    smooth_plus += plus_dm[i];
    smooth_minus += minus_dm[i];
  }
  atr /= period;
  smooth_plus /= period;
  smooth_minus /= period;

  for (int i = 0; i < period; ++i)
    out[i] = 0.0;

  for (size_t i = period; i < candles.size(); ++i) {
    if (i > static_cast<size_t>(period)) {
      atr = (atr * (period - 1) + tr[i]) / period;
      smooth_plus = (smooth_plus * (period - 1) + plus_dm[i]) / period;
      smooth_minus = (smooth_minus * (period - 1) + minus_dm[i]) / period;
    }
    double plus_di = (atr <= 0) ? 0 : (100.0 * smooth_plus / atr);
    double minus_di = (atr <= 0) ? 0 : (100.0 * smooth_minus / atr);
    double di_sum = plus_di + minus_di;
    double dx = (di_sum <= 0) ? 0 : (100.0 * std::abs(plus_di - minus_di) / di_sum);
    out[i] = dx;
  }

  std::vector<double> adx_out(candles.size(), 0.0);
  double adx_smooth = 0;
  for (int i = period; i < period + period && i < static_cast<int>(candles.size()); ++i)
    adx_smooth += out[i];
  adx_smooth /= period;
  for (int i = period; i < period + period && i < static_cast<int>(adx_out.size()); ++i)
    adx_out[i] = adx_smooth;
  for (size_t i = period + period; i < candles.size(); ++i) {
    adx_smooth = (adx_smooth * (period - 1) + out[i]) / period;
    adx_out[i] = adx_smooth;
  }
  return adx_out;
}

double VolumeAverage(const std::vector<Candle>& candles, int period) {
  if (candles.size() < static_cast<size_t>(period) || period < 1) return 0;
  double sum = 0;
  for (size_t i = candles.size() - period; i < candles.size(); ++i)
    sum += candles[i].v;
  return sum / period;
}

bool HasGoldenCross(const std::vector<double>& ema_short, const std::vector<double>& ema_long) {
  if (ema_short.size() < 2 || ema_long.size() < 2) return false;
  size_t i = ema_short.size() - 1;
  size_t j = ema_long.size() - 1;
  return ema_short[i] > ema_long[j] && ema_short[i - 1] <= ema_long[j - 1];
}

bool HasDeadCross(const std::vector<double>& ema_short, const std::vector<double>& ema_long) {
  if (ema_short.size() < 2 || ema_long.size() < 2) return false;
  size_t i = ema_short.size() - 1;
  size_t j = ema_long.size() - 1;
  return ema_short[i] < ema_long[j] && ema_short[i - 1] >= ema_long[j - 1];
}

bool Is4hBullishAlignment(const std::vector<double>& ema_short_4h,
                          const std::vector<double>& ema_mid_4h,
                          const std::vector<double>& ema_long_4h) {
  if (ema_short_4h.empty() || ema_mid_4h.empty() || ema_long_4h.empty()) return false;
  size_t i = ema_short_4h.size() - 1;
  size_t j = ema_mid_4h.size() - 1;
  size_t k = ema_long_4h.size() - 1;
  return ema_short_4h[i] > ema_mid_4h[j] && ema_mid_4h[j] > ema_long_4h[k];
}

bool Is4hBullishAlignmentPartial(const std::vector<double>& ema_short_4h,
                                 const std::vector<double>& ema_mid_4h) {
  if (ema_short_4h.empty() || ema_mid_4h.empty()) return false;
  return ema_short_4h.back() > ema_mid_4h.back();
}

}  // namespace ant_engine
