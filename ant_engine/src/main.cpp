// 개미엔진 (AntEngine) v0.9 — C++
// 트레이딩 엔진. 입출력 연동 가이드 준거. 바이너리 배포용.

#include "ant_engine/engine.hpp"
#include "ant_engine/types.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <cstdlib>
#include <iostream>

namespace {

void Log(const std::string& msg) {
  auto now = std::chrono::system_clock::now();
  auto t = std::chrono::system_clock::to_time_t(now);
  char buf[64];
  std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::gmtime(&t));
  std::cout << "[" << buf << "] " << msg << std::endl;
}

}  // namespace

int main(int argc, char* argv[]) {
  (void)argc;
  (void)argv;

  const char* port_env = std::getenv("ANT_ENGINE_PORT");
  int port = port_env ? std::atoi(port_env) : 9100;
  if (port <= 0 || port > 65535) port = 9100;

  httplib::Server svr;

  svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
    res.set_header("Content-Type", "application/json");
    res.set_content("{\"status\":\"ok\"}", "application/json");
  });

  svr.Get("/version", [](const httplib::Request&, httplib::Response& res) {
    nlohmann::json j;
    j["engine"] = ant_engine::kEngineName;
    j["version"] = ant_engine::kEngineVersion;
    j["schema_version"] = ant_engine::kSchemaVersion;
    res.set_header("Content-Type", "application/json");
    res.set_content(j.dump(), "application/json");
  });

  svr.Post("/signal", [](const httplib::Request& req, httplib::Response& res) {
    Log("POST /signal");
    ant_engine::SignalRequest sig_req;
    try {
      auto body = nlohmann::json::parse(req.body);
      sig_req = body.get<ant_engine::SignalRequest>();
    } catch (const std::exception& e) {
      nlohmann::json err;
      err["schema_version"] = ant_engine::kSchemaVersion;
      err["status"] = "error";
      err["error_code"] = "INVALID_JSON";
      err["error_message"] = e.what();
      res.status = 400;
      res.set_header("Content-Type", "application/json");
      res.set_content(err.dump(), "application/json");
      return;
    }
    nlohmann::json resp = ant_engine::Evaluate(sig_req);
    if (resp.contains("status") && resp["status"] == "error" &&
        resp.contains("error_code") && resp["error_code"] == "INVALID_INPUT") {
      res.status = 400;
    }
    res.set_header("Content-Type", "application/json");
    res.set_content(resp.dump(), "application/json");
  });

  const char* host = "0.0.0.0";
#ifdef _WIN32
  host = "127.0.0.1";  /* Windows에서 0.0.0.0 바인드 실패 시 로컬호스트로 */
#endif
  std::string addr = std::string(host) + ":" + std::to_string(port);
  Log(std::string("[AntEngine ") + ant_engine::kEngineVersion +
      "] schema " + ant_engine::kSchemaVersion + " — listening on " + addr);

  if (!svr.listen(host, static_cast<int>(port))) {
    std::cerr << "Listen failed." << std::endl;
    return 1;
  }
  return 0;
}
