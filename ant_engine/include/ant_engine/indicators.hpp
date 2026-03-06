#ifndef ANT_ENGINE_INDICATORS_HPP
#define ANT_ENGINE_INDICATORS_HPP

#include "types.hpp"
#include <vector>

namespace ant_engine {

// --- 지표 계산 (Jesse/Freqtrade 스타일: 캔들 → 지표값)
// 캔들은 시간순 오름차순(가장 오래된 것이 인덱스 0) 가정.

// EMA(close, period). 반환 벡터 크기 = candles.size(); 앞쪽 period-1개는 유효하지 않을 수 있음.
std::vector<double> ComputeEMA(const std::vector<Candle>& candles, int period);

// RSI(close, period=14). 반환 벡터 크기 = candles.size(); 앞쪽 period개는 NaN 대신 50.0 등 기본값.
std::vector<double> ComputeRSI(const std::vector<Candle>& candles, int period = 14);

// ADX(high, low, close, period=14). 반환 벡터 크기 = candles.size(); 앞쪽 2*period 미만은 유효하지 않을 수 있음.
std::vector<double> ComputeADX(const std::vector<Candle>& candles, int period = 14);

// 마지막 N봉 거래량 평균. candles.size() >= period 필요.
double VolumeAverage(const std::vector<Candle>& candles, int period = 20);

// 골든크로스: 최근 2봉 기준 단기 EMA가 장기 EMA를 아래에서 위로 돌파했는지.
// ema_short, ema_long: 최소 2개 이상 요소. 인덱스는 [size-2], [size-1] 사용.
bool HasGoldenCross(const std::vector<double>& ema_short, const std::vector<double>& ema_long);

// 데드크로스: 최근 2봉 기준 단기 EMA가 장기 EMA를 위에서 아래로 돌파했는지.
bool HasDeadCross(const std::vector<double>& ema_short, const std::vector<double>& ema_long);

// 4h 정배열: 단기 > 중기 > 장기 EMA (최신 봉 기준). 각 벡터는 비어있지 않음.
bool Is4hBullishAlignment(const std::vector<double>& ema_short_4h,
                          const std::vector<double>& ema_mid_4h,
                          const std::vector<double>& ema_long_4h);

// 4h 부분 정배열: 단기 > 중기 (장기 없을 때)
bool Is4hBullishAlignmentPartial(const std::vector<double>& ema_short_4h,
                                 const std::vector<double>& ema_mid_4h);

}  // namespace ant_engine

#endif
