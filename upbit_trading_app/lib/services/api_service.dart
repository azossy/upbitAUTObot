import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// SharedPreferences 키: API 서버 주소
const String kApiBaseUrlKey = 'api_base_url';

/// 4xx/5xx·타임아웃·연결 실패 시 사용자에게 보여줄 한글 메시지 반환 (크래시 없이 복구 가능하도록)
String getApiErrorMessage(dynamic e, {String fallback = '오류가 발생했습니다.'}) {
  if (e is DioException) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return '서버에 연결할 수 없습니다. 네트워크와 백엔드 실행 여부를 확인하세요.';
    }
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      final d = data['detail'];
      return d is String ? d : d.toString();
    }
    if (e.response?.statusCode != null) {
      if (e.response!.statusCode! >= 500) return '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
      if (e.response!.statusCode == 401) return '인증이 필요합니다. 다시 로그인해 주세요.';
      if (e.response!.statusCode == 403) return '권한이 없습니다.';
      if (e.response!.statusCode == 404) return '요청한 항목을 찾을 수 없습니다.';
    }
    return e.message?.toString() ?? fallback;
  }
  return e.toString().isNotEmpty ? e.toString() : fallback;
}

class ApiService {
  static const String defaultBaseUrl = 'http://127.0.0.1:8000';

  String _baseUrl;
  late final Dio _dio;

  String? _accessToken;

  ApiService({String? baseUrl}) : _baseUrl = _normalizeBaseUrl(baseUrl ?? defaultBaseUrl) {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        return handler.next(options);
      },
    ));
  }

  void setToken(String token) => _accessToken = token;
  String? getToken() => _accessToken;
  void clearToken() => _accessToken = null;

  String get baseUrl => _baseUrl;

  /// 저장된 URL로 변경. 끝 / 제거, 앞뒤 공백 제거.
  void updateBaseUrl(String url) {
    final u = url.trim();
    final clean = u.endsWith('/') ? u.substring(0, u.length - 1) : u;
    if (clean.isEmpty) return;
    _baseUrl = clean;
    _dio.options.baseUrl = clean;
  }

  /// SharedPreferences에서 API 서버 주소 로드 후 적용. 앱 기동 시 한 번 호출.
  static String _normalizeBaseUrl(String url) {
    var u = url.trim();
    while (u.endsWith('/') && u.length > 1) {
      u = u.substring(0, u.length - 1);
    }
    return u.isEmpty ? defaultBaseUrl : u;
  }

  static Future<String> loadStoredBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString(kApiBaseUrlKey)?.trim() ?? defaultBaseUrl;
    return _normalizeBaseUrl(url);
  }

  /// API 서버 주소 저장 후 현재 인스턴스에 반영. http/https로 시작해야 유효.
  static Future<bool> saveBaseUrl(String url) async {
    final u = url.trim();
    if (!u.startsWith('http://') && !u.startsWith('https://')) return false;
    final prefs = await SharedPreferences.getInstance();
    final clean = u.endsWith('/') ? u.substring(0, u.length - 1) : u;
    await prefs.setString(kApiBaseUrlKey, clean);
    return true;
  }

  /// 서버 연결 상태 확인. 성공 시 true, 실패 시 false (대시보드/설정에서 "연결됨"/"연결 끊김" 표시용)
  Future<bool> healthCheck() async {
    try {
      final res = await _dio.get('/health');
      return res.data is Map && (res.data['status'] == 'ok');
    } catch (_) {
      return false;
    }
  }

  // Auth
  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await _dio.post('/api/v1/auth/login', data: {
      'email': email,
      'password': password,
    });
    return res.data as Map<String, dynamic>;
  }

  /// 구글 로그인 (id_token 전달)
  Future<Map<String, dynamic>> loginGoogle(String idToken) async {
    final res = await _dio.post('/api/v1/auth/google', data: {'id_token': idToken});
    return res.data as Map<String, dynamic>;
  }

  /// 카카오 로그인 (access_token 전달)
  Future<Map<String, dynamic>> loginKakao(String accessToken) async {
    final res = await _dio.post('/api/v1/auth/kakao', data: {'access_token': accessToken});
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> register(
      String email, String password, String nickname) async {
    final res = await _dio.post('/api/v1/auth/register', data: {
      'email': email,
      'password': password,
      'nickname': nickname,
    });
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMe() async {
    final res = await _dio.get('/api/v1/auth/me');
    return res.data as Map<String, dynamic>;
  }

  /// FCM 토큰 등록 (로그인 후 호출)
  Future<void> registerFcmToken(String token) async {
    await _dio.put('/api/v1/auth/me/fcm-token', data: {'fcm_token': token});
  }

  /// 프로필 조회 (이메일, 별명, 프로필 사진 URL, 선호 언어)
  Future<Map<String, dynamic>> getProfile() async {
    final res = await _dio.get('/api/v1/auth/profile');
    return res.data as Map<String, dynamic>;
  }

  /// 프로필 수정 (별명, 프로필 사진 URL, 선호 언어). null 필드는 변경 안 함.
  Future<Map<String, dynamic>> updateProfile({
    String? nickname,
    String? avatarUrl,
    String? preferredLanguage,
  }) async {
    final data = <String, dynamic>{};
    if (nickname != null) data['nickname'] = nickname;
    if (avatarUrl != null) data['avatar_url'] = avatarUrl;
    if (preferredLanguage != null) data['preferred_language'] = preferredLanguage;
    final res = await _dio.put('/api/v1/auth/profile', data: data);
    return res.data as Map<String, dynamic>;
  }

  /// 프로필 사진 업로드 (카메라/앨범 이미지 → 서버에 저장). 반환: 갱신된 프로필.
  Future<Map<String, dynamic>> uploadAvatar(dynamic imageFile) async {
    final bytes = await imageFile.readAsBytes();
    final name = imageFile.name ?? 'avatar.jpg';
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: name),
    });
    final res = await _dio.post('/api/v1/auth/profile/avatar', data: formData);
    return res.data as Map<String, dynamic>;
  }

  /// 프로필 사진 전체 URL (상대 경로일 때 baseUrl 붙임)
  String avatarFullUrl(String? avatarUrl) {
    if (avatarUrl == null || avatarUrl.isEmpty) return '';
    if (avatarUrl.startsWith('http')) return avatarUrl;
    final base = _baseUrl.endsWith('/') ? _baseUrl : '$_baseUrl/';
    final path = avatarUrl.startsWith('/') ? avatarUrl.substring(1) : avatarUrl;
    return '$base$path';
  }

  /// 실시간 시세 (업비트 ticker 프록시). markets: ['KRW-BTC', 'KRW-ETH', ...]
  Future<List<Map<String, dynamic>>> getTicker(List<String> markets) async {
    if (markets.isEmpty) return [];
    final query = markets.take(20).join(',');
    final res = await _dio.get('/api/v1/market/ticker', queryParameters: {'markets': query});
    final list = res.data as List<dynamic>? ?? [];
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  // Bot
  Future<Map<String, dynamic>> getBotStatus() async {
    final res = await _dio.get('/api/v1/bot/status');
    return res.data as Map<String, dynamic>;
  }

  /// 일별 수익 시계열 (days일, 백엔드 GET /api/v1/bot/pnl-history)
  Future<List<Map<String, dynamic>>> getPnlHistory({int days = 30}) async {
    final res = await _dio.get('/api/v1/bot/pnl-history', queryParameters: {'days': days});
    final list = res.data as List<dynamic>? ?? [];
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<void> startBot() async {
    await _dio.post('/api/v1/bot/start');
  }

  Future<void> stopBot() async {
    await _dio.post('/api/v1/bot/stop');
  }

  Future<List<dynamic>> getPositions() async {
    final res = await _dio.get('/api/v1/bot/positions');
    return res.data as List<dynamic>;
  }

  /// 업비트 원화·코인 잔고 (API 키 필요). 실패 시 { krw: 0, assets: [], error: "..." }
  Future<Map<String, dynamic>> getBalance() async {
    final res = await _dio.get('/api/v1/bot/balance');
    return res.data as Map<String, dynamic>;
  }

  /// 거래내역 (days: 7, 30, 90 등 기간 필터)
  Future<List<dynamic>> getTrades({int? days}) async {
    final res = await _dio.get(
      '/api/v1/bot/trades',
      queryParameters: days != null ? {'days': days} : null,
    );
    return res.data as List<dynamic>;
  }

  /// 거래내역 CSV 내보내기 (선택 기간). UTF-8 CSV 문자열 반환.
  Future<String> getTradesExportCsv({int days = 30}) async {
    final res = await _dio.get<String>(
      '/api/v1/bot/trades/export',
      queryParameters: {'days': days},
      options: Options(responseType: ResponseType.plain),
    );
    return res.data ?? '';
  }

  // API Keys
  Future<List<dynamic>> getApiKeys() async {
    final res = await _dio.get('/api/v1/bot/api-keys');
    return res.data as List<dynamic>;
  }

  Future<void> addApiKey(String accessKey, String secretKey, {String? label}) async {
    await _dio.post('/api/v1/bot/api-keys', data: {
      'access_key': accessKey,
      'secret_key': secretKey,
      if (label != null && label.isNotEmpty) 'label': label,
    });
  }

  Future<void> deleteApiKey(int keyId) async {
    await _dio.delete('/api/v1/bot/api-keys/$keyId');
  }

  // Bot Config
  Future<Map<String, dynamic>> getBotConfig() async {
    final res = await _dio.get('/api/v1/bot/config');
    return res.data as Map<String, dynamic>;
  }

  Future<void> updateBotConfig({
    double? maxInvestmentRatio,
    int? maxPositions,
    double? stopLossPct,
    double? takeProfitPct,
    String? telegramChatId,
  }) async {
    final data = <String, dynamic>{};
    if (maxInvestmentRatio != null) data['max_investment_ratio'] = maxInvestmentRatio;
    if (maxPositions != null) data['max_positions'] = maxPositions;
    if (stopLossPct != null) data['stop_loss_pct'] = stopLossPct;
    if (takeProfitPct != null) data['take_profit_pct'] = takeProfitPct;
    if (telegramChatId != null) data['telegram_chat_id'] = telegramChatId;
    await _dio.put('/api/v1/bot/config', data: data);
  }

  /// 비밀번호 변경 (JWT 필요)
  Future<void> changePassword(String currentPassword, String newPassword) async {
    await _dio.put('/api/v1/auth/password', data: {
      'current_password': currentPassword,
      'new_password': newPassword,
    });
  }

  // 뉴스·공지
  /// 실시간 코인 뉴스 (CryptoCompare 기반)
  Future<List<Map<String, dynamic>>> getCoinNews({int limit = 30}) async {
    final res = await _dio.get('/api/v1/news/coin', queryParameters: {'limit': limit});
    final data = res.data as Map<String, dynamic>?;
    final list = data?['items'] as List<dynamic>? ?? [];
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  /// 업비트 공지사항 (목록 또는 공지 페이지 링크)
  Future<List<Map<String, dynamic>>> getUpbitNotices() async {
    final res = await _dio.get('/api/v1/news/upbit');
    final data = res.data as Map<String, dynamic>?;
    final list = data?['items'] as List<dynamic>? ?? [];
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
}
