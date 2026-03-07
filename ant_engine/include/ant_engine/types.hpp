#ifndef ANT_ENGINE_TYPES_HPP
#define ANT_ENGINE_TYPES_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace ant_engine {

// 입출력 연동 가이드 §2·§3 상수
constexpr const char* kSchemaVersion = "1.0";
constexpr const char* kEngineVersion = "1.1";
constexpr const char* kEngineName    = "AntEngine";

struct Candle {
  std::string t;
  double o = 0, h = 0, l = 0, c = 0, v = 0;
  NLOHMANN_DEFINE_TYPE_INTRUSIVE(Candle, t, o, h, l, c, v)
};

struct Position {
  std::string market;
  double quantity = 0;
  double avg_entry_price = 0;
  std::string entry_timestamp_utc;  // ISO 8601, 시간 손절(7순위) 계산용
  bool sold_tier1 = false;  // 분할 익절 +5% 구간 청산 여부
  bool sold_tier2 = false;
  bool sold_tier3 = false;
  NLOHMANN_DEFINE_TYPE_INTRUSIVE(Position, market, quantity, avg_entry_price, entry_timestamp_utc, sold_tier1, sold_tier2, sold_tier3)
};

struct Config {
  int max_positions = 7;
  double stop_loss_pct = 2.5;
  double take_profit_pct = 7.0;
  double take_profit_tier1_pct = 5.0;
  double take_profit_tier2_pct = 10.0;
  double take_profit_tier3_pct = 15.0;
  int time_stop_hours = 12;
  double max_investment_ratio = 0.5;
  bool event_window_active = false;
  // 진입 완화 오버라이드 (0이면 엔진 기본값 사용)
  double adx_entry_threshold = 0;   // 2차: 기본 25
  double ema_tolerance_pct = 0;     // 3차 A안: 기본 0.01
  double rsi_pullback_max = 0;      // 3차 A안: 기본 50
  double market_score_strong = 0;   // 3차 B안: 기본 8
  double adx_strong_1h = 0;        // 3차 B안: 기본 35
  double adx_strong_4h = 0;        // 3차 B안: 기본 30
  bool allow_entry_3c = false;      // 3차 C안(2차+RSI 40~60) 허용 여부
  NLOHMANN_DEFINE_TYPE_INTRUSIVE(Config,
    max_positions, stop_loss_pct, take_profit_pct,
    take_profit_tier1_pct, take_profit_tier2_pct, take_profit_tier3_pct,
    time_stop_hours, max_investment_ratio, event_window_active,
    adx_entry_threshold, ema_tolerance_pct, rsi_pullback_max,
    market_score_strong, adx_strong_1h, adx_strong_4h, allow_entry_3c)
};

// §2 입력
struct SignalRequest {
  std::string request_id;
  std::string timestamp_utc;
  std::string market;
  std::string mode;  // "entry" | "exit" | "both"
  std::vector<Candle> candles_1h;
  std::vector<Candle> candles_4h;
  double current_price = 0;
  std::vector<Position> positions;
  double balance_krw = 0;
  Config config;
  std::string market_regime;  // "up" | "sideways" | "down", 1차 진입·1순위/7순위 매각용
  double market_score = 0;    // 국면 점수, 7순위 시간손절 3차 조건용(선택)
  NLOHMANN_DEFINE_TYPE_INTRUSIVE(SignalRequest,
    request_id, timestamp_utc, market, mode,
    candles_1h, candles_4h, current_price, positions, balance_krw, config,
    market_regime, market_score)
};

}  // namespace ant_engine

#endif
