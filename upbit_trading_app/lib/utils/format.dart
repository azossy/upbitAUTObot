// 공용 포맷 유틸 (금액 등)
//
// 앱 내 모든 금액 표기: 한국식 천 단위 콤마 사용, 숫자는 우측 정렬.
// 비율(%) 표기: 숫자는 가운데 정렬.

/// 한국식 천 단위 콤마 (예: 999,999,999)
String formatKrw(num value) {
  final s = value.toInt().abs().toString();
  final buf = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
    buf.write(s[i]);
  }
  return buf.toString();
}
