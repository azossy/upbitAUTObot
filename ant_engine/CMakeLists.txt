cmake_minimum_required(VERSION 3.14)
project(ant_engine VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# nlohmann/json (release tarball). Target: nlohmann_json::nlohmann_json
include(FetchContent)
FetchContent_Declare(nlohmann_json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
set(JSON_BuildTests OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(nlohmann_json)

# cpp-httplib (header-only, fetch single header or use FetchContent)
FetchContent_Declare(httplib
  GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
  GIT_TAG        v0.14.3
)
FetchContent_MakeAvailable(httplib)

add_executable(ant_engine
  src/main.cpp
  src/engine.cpp
  src/indicators.cpp
)

# Linux(서버) 빌드 시 출력 파일명: AntEngine-버전.bin
if(UNIX AND NOT APPLE)
  set_target_properties(ant_engine PROPERTIES OUTPUT_NAME "AntEngine-${PROJECT_VERSION}.bin")
endif()

target_include_directories(ant_engine PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${nlohmann_json_SOURCE_DIR}/include
  ${httplib_SOURCE_DIR}
)

# Windows: Winsock for cpp-httplib
if(WIN32)
  target_link_libraries(ant_engine PRIVATE ws2_32)
endif()

target_link_libraries(ant_engine PRIVATE
  nlohmann_json::nlohmann_json
)

# Windows: avoid console window for release build (optional)
if(WIN32)
  # keep console for debugging; comment next line to show console
  # set_target_properties(ant_engine PROPERTIES WIN32_EXECUTABLE TRUE)
endif()
