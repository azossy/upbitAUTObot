import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../l10n/app_localizations.dart';

/// 현재 앱 표시 언어 코드 (예: 'ko', 'en'). 변경 시 앱 전체가 해당 언어로 갱신됨.
final localeProvider = StateProvider<String>((ref) => 'ko');

/// 현재 Locale (MaterialApp.locale 용)
final appLocaleProvider = Provider<Locale>((ref) {
  final code = ref.watch(localeProvider);
  return Locale(code);
});

/// 현재 언어의 AppLocalizations
final appLocalizationsProvider = Provider<AppLocalizations>((ref) {
  final code = ref.watch(localeProvider);
  return AppLocalizations(code);
});
