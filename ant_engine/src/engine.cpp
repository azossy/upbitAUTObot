#include "ant_engine/engine.hpp"
#include "ant_engine/indicators.hpp"
#include "ant_engine/types.hpp"
#include <nlohmann/json.hpp>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <cstdlib>
#include <ctime>

namespace ant_engine {

namespace {

constexpr int kEmaShort = 12;
constexpr int kEmaLong = 26;
constexpr int kEmaMid4h = 20;
constexpr int kEmaLong4h = 50;
constexpr int kAdxPeriod = 14;
constexpr int kRsiPeriod = 14;
constexpr int kVolumePeriod = 20;
constexpr int kMinCandles1h = 26;
constexpr int kMinCandles4h = 50;
// 기본값 = 진입 완화 적용순서 프로필2 (방안1+2: ADX22, EMA 2%, RSI 55)
constexpr double kAdxEntryThreshold = 22.0;
constexpr double kAdxStrongTrend = 35.0;
constexpr double kAdx4hStrong = 30.0;
constexpr double kRsiPullbackMax = 55.0;
constexpr double kMarketScoreStrong = 8.0;
constexpr double kEmaTolerancePct = 0.02;
constexpr double kTimeStopPnlMin = -0.5;
constexpr double kTimeStopPnlMax = 1.5;

std::string NowUtcIso8601() {
  auto now = std::chrono::system_clock::now();
  auto time = std::chrono::system_clock::to_time_t(now);
  std::ostringstream os;
  os << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
  return os.str();
}

// UTC 기준 1970-01-01 이후 일수 계산 (윤년 포함).
static int DaysSinceEpoch(int y, int mo, int d) {
  if (mo <= 2) { y--; mo += 12; }
  int k = 365 * y + y / 4 - y / 100 + y / 400;
  int m = (153 * (mo - 3) + 2) / 5 + 1;
  return k + m + d - 719468;  // 719468 = 1970-01-01 UTC 기준 일수
}

// ISO 8601 "YYYY-MM-DDTHH:MM:SSZ" -> time_t (UTC). 실패 시 0.
// mktime은 로컬 시간으로 해석하므로 UTC 기준으로 직접 계산.
std::time_t ParseIso8601Utc(const std::string& s) {
  if (s.size() < 19) return 0;
  int y, mo, d, h, mi, sec;
  if (std::sscanf(s.c_str(), "%d-%d-%dT%d:%d:%d", &y, &mo, &d, &h, &mi, &sec) != 6)
    return 0;
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return 0;
  int days = DaysSinceEpoch(y, mo, d);
  return static_cast<std::time_t>(days) * 86400 + h * 3600 + mi * 60 + sec;
}

nlohmann::json BaseResponse(const SignalRequest& req) {
  nlohmann::json j;
  j["request_id"] = req.request_id;
  j["timestamp_utc"] = NowUtcIso8601();
  j["schema_version"] = kSchemaVersion;
  j["status"] = "ok";
  j["market"] = req.market;
  j["metadata"] = nlohmann::json::object();
  j["metadata"]["engine_version"] = kEngineVersion;
  return j;
}

void SetError(nlohmann::json& j, const std::string& code, const std::string& msg) {
  j["status"] = "error";
  j["error_code"] = code;
  j["error_message"] = msg;
  j.erase("market");
  j.erase("signal");
  j.erase("reason_code");
  j.erase("reason_text");
  j.erase("side");
  j.erase("quantity");
  j.erase("price_limit");
  j.erase("metadata");
}

// --- 지표 단계: 1h/4h 캔들로부터 지표 계산
struct IndicatorContext {
  std::vector<double> ema_short_1h, ema_long_1h;
  std::vector<double> ema_short_4h, ema_mid_4h, ema_long_4h;
  std::vector<double> adx_1h, adx_4h;
  std::vector<double> rsi_1h;
  double vol_avg_20_1h = 0;
  bool valid_1h = false;
  bool valid_4h = false;
};

IndicatorContext ComputeIndicators(const SignalRequest& req) {
  IndicatorContext ctx;
  if (req.candles_1h.size() >= static_cast<size_t>(kMinCandles1h)) {
    ctx.ema_short_1h = ComputeEMA(req.candles_1h, kEmaShort);
    ctx.ema_long_1h = ComputeEMA(req.candles_1h, kEmaLong);
    ctx.adx_1h = ComputeADX(req.candles_1h, kAdxPeriod);
    ctx.rsi_1h = ComputeRSI(req.candles_1h, kRsiPeriod);
    ctx.vol_avg_20_1h = VolumeAverage(req.candles_1h, kVolumePeriod);
    ctx.valid_1h = true;
  }
  if (req.candles_4h.size() >= static_cast<size_t>(kEmaLong)) {
    ctx.ema_short_4h = ComputeEMA(req.candles_4h, kEmaShort);
    ctx.ema_mid_4h = ComputeEMA(req.candles_4h, kEmaMid4h);
    ctx.adx_4h = ComputeADX(req.candles_4h, kAdxPeriod);
    ctx.valid_4h = true;
    if (req.candles_4h.size() >= static_cast<size_t>(kMinCandles4h))
      ctx.ema_long_4h = ComputeEMA(req.candles_4h, kEmaLong4h);
  }
  return ctx;
}

// --- 진입 1차: 시장 국면 상승 + 슬롯 존재
bool PassEntryStage1(const SignalRequest& req) {
  if (req.market_regime == "down" || req.market_regime == "sideways") return false;
  return static_cast<int>(req.positions.size()) < req.config.max_positions;
}

// --- 1h 정배열: 단기 EMA > 장기 EMA (골든크로스 직후 구간 포함)
static bool Is1hBullishAlignment(const IndicatorContext& ctx) {
  if (ctx.ema_short_1h.empty() || ctx.ema_long_1h.empty()) return false;
  return ctx.ema_short_1h.back() > ctx.ema_long_1h.back();
}

// config 오버라이드 반영 (0이면 기본값 사용)
static double AdxEntryThreshold(const SignalRequest& req) {
  return req.config.adx_entry_threshold > 0 ? req.config.adx_entry_threshold : kAdxEntryThreshold;
}
static double EmaTolerancePct(const SignalRequest& req) {
  return req.config.ema_tolerance_pct > 0 ? req.config.ema_tolerance_pct : kEmaTolerancePct;
}
static double RsiPullbackMax(const SignalRequest& req) {
  return req.config.rsi_pullback_max > 0 ? req.config.rsi_pullback_max : kRsiPullbackMax;
}
static double MarketScoreStrong(const SignalRequest& req) {
  return req.config.market_score_strong > 0 ? req.config.market_score_strong : kMarketScoreStrong;
}
static double AdxStrong1h(const SignalRequest& req) {
  return req.config.adx_strong_1h > 0 ? req.config.adx_strong_1h : kAdxStrongTrend;
}
static double AdxStrong4h(const SignalRequest& req) {
  return req.config.adx_strong_4h > 0 ? req.config.adx_strong_4h : kAdx4hStrong;
}

// --- 진입 2차: 1h 정배열, 4h 정배열, ADX>=문턱.
bool PassEntryStage2(const SignalRequest& req, const IndicatorContext& ctx) {
  if (!ctx.valid_1h) return false;
  if (!Is1hBullishAlignment(ctx)) return false;
  if (ctx.valid_4h) {
    if (ctx.ema_long_4h.empty()) {
      if (!Is4hBullishAlignmentPartial(ctx.ema_short_4h, ctx.ema_mid_4h)) return false;
    } else {
      if (!Is4hBullishAlignment(ctx.ema_short_4h, ctx.ema_mid_4h, ctx.ema_long_4h)) return false;
    }
  }
  double adx_thr = AdxEntryThreshold(req);
  if (ctx.adx_1h.empty() || ctx.adx_1h.back() < adx_thr) return false;
  return true;
}

// --- 진입 3차 A안: 눌림목 — 가격이 단기 EMA 근처, RSI<=문턱, 거래량<=평균
bool PassEntryStage3A(const SignalRequest& req, const IndicatorContext& ctx) {
  if (!ctx.valid_1h || ctx.ema_short_1h.empty() || ctx.rsi_1h.empty()) return false;
  double ema_s = ctx.ema_short_1h.back();
  if (ema_s <= 0) return false;
  double tol_pct = EmaTolerancePct(req);
  double tol = ema_s * tol_pct;
  if (req.current_price < ema_s - tol || req.current_price > ema_s + tol) return false;
  if (ctx.rsi_1h.back() > RsiPullbackMax(req)) return false;
  if (ctx.vol_avg_20_1h <= 0 || req.candles_1h.back().v > ctx.vol_avg_20_1h) return false;
  return true;
}

// --- 진입 3차 B안: 강한 추세 — 시장점수·ADX 문턱
bool PassEntryStage3B(const SignalRequest& req, const IndicatorContext& ctx) {
  double score_thr = MarketScoreStrong(req);
  if (req.market_score < score_thr) return false;
  double adx1 = AdxStrong1h(req), adx4 = AdxStrong4h(req);
  if (!ctx.valid_1h || ctx.adx_1h.empty() || ctx.adx_1h.back() < adx1) return false;
  if (!ctx.valid_4h || ctx.adx_4h.empty() || ctx.adx_4h.back() < adx4) return false;
  return true;
}

// --- 진입 3차 C안: 2차 통과 + 가격이 4h 단기 EMA 위 + RSI 40~60 (옵션)
bool PassEntryStage3C(const SignalRequest& req, const IndicatorContext& ctx) {
  if (!ctx.valid_1h || ctx.rsi_1h.empty()) return false;
  double rsi = ctx.rsi_1h.back();
  if (rsi < 40.0 || rsi > 60.0) return false;
  if (!ctx.valid_4h || ctx.ema_short_4h.empty()) return false;
  if (req.current_price <= ctx.ema_short_4h.back()) return false;
  if (ctx.vol_avg_20_1h > 0 && req.candles_1h.back().v > ctx.vol_avg_20_1h * 1.5) return false;
  return true;
}

// --- 매각 1순위: 국면 하락 전환
bool ExitRank1RegimeDown(const SignalRequest& req) {
  return req.market_regime == "down";
}

// --- 매각 3순위: 데드크로스 + ADX<문턱 (2차 확인)
bool ExitRank3DeadCross(const SignalRequest& req, const IndicatorContext& ctx) {
  if (!ctx.valid_1h) return false;
  if (!HasDeadCross(ctx.ema_short_1h, ctx.ema_long_1h)) return false;
  double adx_thr = AdxEntryThreshold(req);
  return !ctx.adx_1h.empty() && ctx.adx_1h.back() < adx_thr;
}

// --- 매각 7순위: 시간 손절 — 12시간 경과 + 수익률 -0.5%~+1.5% + 국면/ADX 약화
bool ExitRank7TimeStop(const SignalRequest& req, const Position& pos, const IndicatorContext& ctx) {
  if (pos.entry_timestamp_utc.empty()) return false;
  std::time_t entry_t = ParseIso8601Utc(pos.entry_timestamp_utc);
  std::time_t now_t = ParseIso8601Utc(req.timestamp_utc);
  if (entry_t == 0 || now_t == 0) return false;
  const int hours = req.config.time_stop_hours > 0 ? req.config.time_stop_hours : 12;
  if (now_t - entry_t < hours * 3600) return false;
  double pnl_pct = (req.current_price - pos.avg_entry_price) / pos.avg_entry_price * 100.0;
  if (pnl_pct < kTimeStopPnlMin || pnl_pct > kTimeStopPnlMax) return false;
  if (!ctx.adx_1h.empty() && ctx.adx_1h.back() > 20.0) return false;
  return true;
}

}  // namespace

nlohmann::json Evaluate(const SignalRequest& req) {
  nlohmann::json resp = BaseResponse(req);

  if (req.market.empty()) {
    SetError(resp, "INVALID_INPUT", "market 필수");
    return resp;
  }
  if (req.mode != "entry" && req.mode != "exit" && req.mode != "both") {
    SetError(resp, "INVALID_INPUT", "mode는 entry|exit|both 중 하나");
    return resp;
  }

  if (req.config.event_window_active && (req.mode == "entry" || req.mode == "both")) {
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_event_window";
    resp["reason_text"] = "미국 거시 이벤트 창 — 진입 보류";
    resp["allocation_score"] = 0;
    return resp;
  }

  IndicatorContext ctx;
  if (req.mode == "exit" || req.mode == "both")
    ctx = ComputeIndicators(req);

  // ---------- 매각 판단 (1~7순위)
  if (!req.positions.empty() && (req.mode == "exit" || req.mode == "both")) {
    for (const auto& pos : req.positions) {
      if (pos.market != req.market) continue;
      if (pos.avg_entry_price <= 0) continue;
      double pnl_pct = (req.current_price - pos.avg_entry_price) / pos.avg_entry_price * 100.0;

      if (ExitRank1RegimeDown(req)) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_market_downturn";
        resp["reason_text"] = "국면 하락 전환";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        resp["allocation_score"] = (pnl_pct >= 0 ? 6 : 3);
        return resp;
      }
      if (pnl_pct <= -req.config.stop_loss_pct) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_stop_loss";
        resp["reason_text"] = "손절 조건 충족";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        resp["allocation_score"] = 3;
        return resp;
      }
      if (ExitRank3DeadCross(req, ctx)) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_dead_cross";
        resp["reason_text"] = "데드크로스 + ADX 약화";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        resp["allocation_score"] = (pnl_pct >= 0 ? 6 : 3);
        return resp;
      }
      if (pnl_pct >= req.config.take_profit_tier3_pct && !pos.sold_tier3) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_take_profit_tier3";
        resp["reason_text"] = "분할 익절 +15% 구간";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity * 0.25;
        resp["allocation_score"] = 6;
        return resp;
      }
      if (pnl_pct >= req.config.take_profit_tier2_pct && !pos.sold_tier2) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_take_profit_tier2";
        resp["reason_text"] = "분할 익절 +10% 구간";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity * 0.25;
        resp["allocation_score"] = 6;
        return resp;
      }
      if (pnl_pct >= req.config.take_profit_tier1_pct && !pos.sold_tier1) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_take_profit_tier1";
        resp["reason_text"] = "분할 익절 +5% 구간";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity * 0.25;
        resp["allocation_score"] = 6;
        return resp;
      }
      if (ExitRank7TimeStop(req, pos, ctx)) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_time_stop";
        resp["reason_text"] = "시간 손절";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        resp["allocation_score"] = (pnl_pct >= 0 ? 6 : 3);
        return resp;
      }
      if (pnl_pct >= req.config.take_profit_pct) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_take_profit";
        resp["reason_text"] = "익절 조건 충족";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        resp["allocation_score"] = 6;
        return resp;
      }
    }
  }

  // ---------- 진입 판단
  if (req.candles_1h.size() < static_cast<size_t>(kMinCandles1h) &&
      (req.mode == "entry" || req.mode == "both")) {
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_no_signal";
    resp["reason_text"] = "1시간봉 데이터 부족(최소 " + std::to_string(kMinCandles1h) + "개)";
    resp["allocation_score"] = 0;
    return resp;
  }

  if (req.mode == "entry" || req.mode == "both") {
    ctx = ComputeIndicators(req);
    if (!PassEntryStage1(req)) {
      resp["signal"] = "hold";
      resp["reason_code"] = "hold_stage1";
      resp["reason_text"] = "1차 미통과(국면 또는 슬롯)";
      resp["allocation_score"] = 0;
      return resp;
    }
    if (!PassEntryStage2(req, ctx)) {
      resp["signal"] = "hold";
      resp["reason_code"] = "hold_stage2";
      resp["reason_text"] = "2차 미통과(1h·4h 정배열/ADX)";
      resp["allocation_score"] = 2;
      return resp;
    }
    if (PassEntryStage3A(req, ctx)) {
      resp["signal"] = "buy";
      resp["reason_code"] = "entry_1_2_3_ok";
      resp["reason_text"] = "3차 A안 눌림목 진입";
      resp["side"] = "buy";
      resp["quantity"] = 0;
      resp["allocation_score"] = 8;
      return resp;
    }
    if (PassEntryStage3B(req, ctx)) {
      resp["signal"] = "buy";
      resp["reason_code"] = "entry_1_2_3_ok_strong";
      resp["reason_text"] = "3차 B안 강한 추세 즉시 진입";
      resp["side"] = "buy";
      resp["quantity"] = 0;
      resp["allocation_score"] = 8;
      return resp;
    }
    if (req.config.allow_entry_3c && PassEntryStage3C(req, ctx)) {
      resp["signal"] = "buy";
      resp["reason_code"] = "entry_1_2_3_ok_c";
      resp["reason_text"] = "3차 C안 2차+RSI 40~60 진입";
      resp["side"] = "buy";
      resp["quantity"] = 0;
      resp["allocation_score"] = 8;
      return resp;
    }
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_stage3";
    resp["reason_text"] = "3차 미통과(진입 타이밍 대기)";
    resp["allocation_score"] = 4;
    return resp;
  }

  resp["signal"] = "hold";
  resp["reason_code"] = "hold_no_signal";
  resp["reason_text"] = "시그널 없음";
  resp["allocation_score"] = 1;
  return resp;
}

}  // namespace ant_engine
