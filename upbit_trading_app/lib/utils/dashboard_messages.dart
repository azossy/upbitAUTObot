// 대시보드 안내 메시지 — 상황에 따라 하나 선택해 표시 (친절·기분 좋은 문구)

/// 상황 타입 (우선순위 순으로 판단)
enum DashboardMessageType {
  noApiKey,
  apiKeyError,
  firstVisitToday,
  returnUser,
  profitCongrats,
  smallProfit,
  lossEncourage,
  noPositionYet,
  botRunning,
  botStopped,
  welcomeNew,
  defaultGreeting,
}

/// 닉네임 치환: {name} → 실제 닉네임
String _applyName(String text, String nickname) {
  final name = nickname.trim().isEmpty ? '회원' : nickname;
  return text.replaceAll('{name}', name).replaceAll('{n}', name);
}

/// 상황별 메시지 풀 (50개 근처). 상황 판단 후 하나 반환.
class DashboardMessages {
  static const _noApiKey = [
    '아직 업비트 API 키가 등록되지 않았습니다. 설정에서 키를 등록해 주세요.',
    'API 키를 등록하면 자동매매를 시작할 수 있어요. 설정 메뉴에서 등록해 주세요.',
    '원하시는 거래를 위해 설정에서 업비트 API 키를 등록해 주세요.',
  ];

  static const _apiKeyError = [
    'API 키를 확인해 주세요. 설정에서 다시 등록하시면 해결될 수 있습니다.',
    '키 값에 문제가 있을 수 있습니다. 설정에서 API 키를 확인해 주세요.',
  ];

  static const _firstVisitToday = [
    '{name}님, 안녕하세요? 오늘은 대박 나시길 기원합니다!',
    '{name}님, 좋은 하루 되세요! 오늘도 수익 나시길 바랍니다.',
    '{name}님, 오늘 하루도 화이팅이에요!',
    '오늘도 {name}님의 하루가 풍성하길 바랍니다.',
    '{name}님, 반갑습니다! 오늘 하루 좋은 일만 가득하세요.',
  ];

  static const _returnUser = [
    '{name}님, 오랜만에 오셨네요. 정말 반갑습니다.',
    '{name}님, 다시 찾아와 주셔서 감사해요. 언제나 환영입니다.',
    '오랜만이에요, {name}님. 오늘도 좋은 하루 되세요.',
    '{name}님, 반가워요. 오늘도 함께해 주셔서 감사합니다.',
  ];

  static const _profitCongrats = [
    '{name}님, 수익이 났어요. 축하합니다.',
    '수익이 발생했어요. {name}님, 정말 잘하셨습니다. 축하드려요.',
    '{name}님, 수익 나셨네요. 축하합니다.',
    '수익 축하드려요, {name}님. 오늘도 좋은 하루 되세요.',
    '{name}님, 수익 나셨다니 기쁘네요. 축하드립니다.',
  ];

  static const _smallProfit = [
    '{name}님, 조금이라도 수익이 나셨다니 다행이에요. 오늘도 화이팅!',
    '소소한 수익도 의미 있어요. {name}님, 오늘도 좋은 하루 되세요.',
  ];

  static const _lossEncourage = [
    '{name}님, 오늘은 조금 아쉽지만 내일은 더 좋은 날이 올 거예요. 응원합니다.',
    '일시적인 조정일 수 있어요. {name}님, 침착하게 다음 기회를 노려 보세요.',
    '{name}님, 무리하지 마시고 여유 있게 운영해 보세요. 응원할게요.',
  ];

  static const _noPositionYet = [
    '아직 보유 포지션이 없어요. 봇을 시작하면 자동으로 매매가 진행됩니다.',
    '설정을 확인한 뒤 봇을 시작해 보세요. {name}님을 응원할게요.',
  ];

  static const _botRunning = [
    '봇이 열심히 일하고 있어요. {name}님은 편히 보시면 됩니다.',
    '자동매매가 진행 중이에요. {name}님, 편히 확인만 하셔도 돼요.',
  ];

  static const _botStopped = [
    '봇이 대기 중이에요. 시작 버튼을 누르면 자동매매가 진행됩니다.',
    '준비가 되셨으면 시작 버튼을 눌러 보세요. {name}님을 응원해요.',
  ];

  static const _welcomeNew = [
    '{name}님, 배짱이에 오신 것을 환영합니다. 설정에서 API 키를 등록한 뒤 봇을 시작해 주세요.',
    '환영해요, {name}님. 차근차근 설정만 하시면 바로 사용하실 수 있어요.',
  ];

  static const _defaultGreeting = [
    '{name}님, 안녕하세요. 오늘도 좋은 하루 되세요.',
    '반갑습니다, {name}님. 편히 이용해 주세요.',
    '{name}님, 언제나 환영이에요. 궁금한 점이 있으면 설정을 확인해 보세요.',
    '오늘도 {name}님과 함께할 수 있어 기쁘네요.',
    '{name}님, 좋은 하루 보내세요. 필요한 것이 있으면 설정을 활용해 주세요.',
    '안녕하세요, {name}님. 오늘 하루도 수고 많으셨어요.',
    '{name}님, 반가워요. 무리하지 않게 운영해 보세요.',
    '언제나 {name}님 곁에 있을게요. 편히 사용해 주세요.',
  ];

  static final _random = _RandomPicker();

  /// 상황에 맞는 안내 문구 하나 반환 (닉네임 적용)
  static String getMessage({
    required DashboardMessageType type,
    required String nickname,
  }) {
    List<String> list;
    switch (type) {
      case DashboardMessageType.noApiKey:
        list = _noApiKey;
        break;
      case DashboardMessageType.apiKeyError:
        list = _apiKeyError;
        break;
      case DashboardMessageType.firstVisitToday:
        list = _firstVisitToday;
        break;
      case DashboardMessageType.returnUser:
        list = _returnUser;
        break;
      case DashboardMessageType.profitCongrats:
        list = _profitCongrats;
        break;
      case DashboardMessageType.smallProfit:
        list = _smallProfit;
        break;
      case DashboardMessageType.lossEncourage:
        list = _lossEncourage;
        break;
      case DashboardMessageType.noPositionYet:
        list = _noPositionYet;
        break;
      case DashboardMessageType.botRunning:
        list = _botRunning;
        break;
      case DashboardMessageType.botStopped:
        list = _botStopped;
        break;
      case DashboardMessageType.welcomeNew:
        list = _welcomeNew;
        break;
      case DashboardMessageType.defaultGreeting:
        list = _defaultGreeting;
        break;
    }
    return _applyName(_random.one(list), nickname);
  }

  /// 현재 상태로 메시지 타입 결정 (우선순위 순)
  static DashboardMessageType resolveType({
    required bool hasApiKeyError,
    required bool hasBalanceError,
    required bool isFirstVisitToday,
    required bool isReturnUser,
    required double? dailyPnl,
    required double? weeklyPnl,
    required bool hasPositions,
    required bool botRunning,
    required bool isNewUser,
  }) {
    if (hasApiKeyError || (hasBalanceError && !hasPositions)) {
      return DashboardMessageType.noApiKey;
    }
    if (isNewUser) return DashboardMessageType.welcomeNew;
    if (isReturnUser) return DashboardMessageType.returnUser;
    if (isFirstVisitToday) return DashboardMessageType.firstVisitToday;
    if (dailyPnl != null && dailyPnl > 5) return DashboardMessageType.profitCongrats;
    if (weeklyPnl != null && weeklyPnl > 3) return DashboardMessageType.profitCongrats;
    if (dailyPnl != null && dailyPnl > 0 && dailyPnl <= 5) return DashboardMessageType.smallProfit;
    if (weeklyPnl != null && weeklyPnl < -2) return DashboardMessageType.lossEncourage;
    if (!hasPositions && !botRunning) return DashboardMessageType.noPositionYet;
    if (botRunning) return DashboardMessageType.botRunning;
    if (!botRunning) return DashboardMessageType.botStopped;
    return DashboardMessageType.defaultGreeting;
  }
}

class _RandomPicker {
  String one(List<String> list) {
    if (list.isEmpty) return '';
    final i = DateTime.now().millisecondsSinceEpoch % list.length;
    return list[i];
  }
}
