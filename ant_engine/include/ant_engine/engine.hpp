#ifndef ANT_ENGINE_ENGINE_HPP
#define ANT_ENGINE_ENGINE_HPP

#include "types.hpp"
#include <nlohmann/json_fwd.hpp>

namespace ant_engine {

// 입출력 가이드 §2·§3 준거. v0.9: 최소 검증 + 보류/진입/매각 골격.
// 반환: §3 출력 JSON 객체 (omitempty 필드는 비어있으면 제외)
nlohmann::json Evaluate(const SignalRequest& req);

}  // namespace ant_engine

#endif
