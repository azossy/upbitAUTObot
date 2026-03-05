#include "ant_engine/engine.hpp"
#include "ant_engine/types.hpp"
#include <nlohmann/json.hpp>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace ant_engine {

namespace {

std::string NowUtcIso8601() {
  auto now = std::chrono::system_clock::now();
  auto time = std::chrono::system_clock::to_time_t(now);
  std::ostringstream os;
  os << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
  return os.str();
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

  // v0.9: 이벤트 창 활성 시 진입 보류
  if (req.config.event_window_active && (req.mode == "entry" || req.mode == "both")) {
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_event_window";
    resp["reason_text"] = "미국 거시 이벤트 창 — 진입 보류";
    return resp;
  }

  // v0.9: 보유 포지션 있으면 매각 판단(손절/익절)
  if (!req.positions.empty() && (req.mode == "exit" || req.mode == "both")) {
    for (const auto& pos : req.positions) {
      if (pos.market != req.market) continue;
      if (pos.avg_entry_price <= 0) continue;
      double pnl_pct = (req.current_price - pos.avg_entry_price) / pos.avg_entry_price * 100.0;
      if (pnl_pct <= -req.config.stop_loss_pct) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_stop_loss";
        resp["reason_text"] = "손절 조건 충족";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        return resp;
      }
      if (pnl_pct >= req.config.take_profit_pct) {
        resp["signal"] = "sell";
        resp["reason_code"] = "exit_take_profit";
        resp["reason_text"] = "익절 조건 충족";
        resp["side"] = "sell";
        resp["quantity"] = pos.quantity;
        return resp;
      }
    }
  }

  // v0.9: 진입 판단 — 캔들 최소 개수
  const int min_candles_1h = 24;
  if (req.candles_1h.size() < static_cast<size_t>(min_candles_1h) &&
      (req.mode == "entry" || req.mode == "both")) {
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_no_signal";
    resp["reason_text"] = "1시간봉 데이터 부족(최소 24개)";
    return resp;
  }

  if (req.mode == "entry" || req.mode == "both") {
    resp["signal"] = "hold";
    resp["reason_code"] = "hold_no_signal";
    resp["reason_text"] = "1차 조건 미충족 (v0.9 골격)";
    return resp;
  }

  resp["signal"] = "hold";
  resp["reason_code"] = "hold_no_signal";
  resp["reason_text"] = "시그널 없음";
  return resp;
}

}  // namespace ant_engine
