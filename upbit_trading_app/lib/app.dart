import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'presentation/screens/login_screen.dart';
import 'presentation/screens/register_screen.dart';
import 'presentation/screens/dashboard_screen.dart';
import 'presentation/screens/positions_screen.dart';
import 'presentation/screens/trades_screen.dart';
import 'presentation/screens/settings_screen.dart';
import 'presentation/screens/password_change_screen.dart';
import 'presentation/screens/news_screen.dart';
import 'presentation/screens/my_screen.dart';
import 'theme/app_theme.dart';
import 'l10n/app_localizations.dart';
import 'providers/locale_provider.dart';
import 'services/auth_provider.dart';
import 'services/api_service.dart';
import 'package:firebase_core/firebase_core.dart';

class UpbitTradingApp extends ConsumerStatefulWidget {
  const UpbitTradingApp({super.key});

  @override
  ConsumerState<UpbitTradingApp> createState() => _UpbitTradingAppState();
}

class _UpbitTradingAppState extends ConsumerState<UpbitTradingApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = _createRouter();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _setupFcmDeepLink();
      _loadStoredApiBaseUrl();
    });
  }

  void _loadStoredApiBaseUrl() {
    ApiService.loadStoredBaseUrl().then((url) {
      ref.read(apiServiceProvider).updateBaseUrl(url);
    });
  }

  void _setupFcmDeepLink() {
    try {
      if (Firebase.apps.isEmpty) return;
      final service = ref.read(notificationServiceProvider);
      service.onMessageOpenedApp.listen((_) => _router.go('/'));
      service.initialMessage.then((msg) {
        if (msg != null) _router.go('/');
      });
    } catch (_) {}
  }

  GoRouter _createRouter() {
    return GoRouter(
      initialLocation: '/login',
      redirect: (context, state) {
        try {
          final loggedIn = ref.read(authStateProvider).isLoggedIn;
          final isAuthRoute = state.matchedLocation == '/login' || state.matchedLocation == '/register';
          if (!isAuthRoute && !loggedIn) return '/login';
          if (isAuthRoute && loggedIn) return '/';
        } catch (e, st) {
          debugPrint('[Router] redirect error: $e $st');
          return '/login';
        }
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
        GoRoute(
          path: '/',
          builder: (_, __) => const DashboardScreen(),
          routes: [
            GoRoute(path: 'positions', builder: (_, __) => const PositionsScreen()),
            GoRoute(path: 'trades', builder: (_, __) => const TradesScreen()),
            GoRoute(path: 'news', builder: (_, __) => const NewsScreen()),
            GoRoute(path: 'my', builder: (_, __) => const MyScreen()),
            GoRoute(path: 'settings', builder: (_, __) => const SettingsScreen(), routes: [
              GoRoute(path: 'password', builder: (_, __) => const PasswordChangeScreen()),
            ]),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final locale = ref.watch(appLocaleProvider);
    final supportedLocales = AppLocalizations.supportedLocales.map((e) => Locale(e)).toList();
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: '배짱이',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      locale: locale,
      supportedLocales: supportedLocales,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: _router,
      builder: (context, child) {
        if (child == null) return const _FallbackScaffold();
        return child;
      },
    );
  }
}

/// 라우터가 화면을 그리지 못할 때 표시 (빈 회색 화면 방지, One UI 스타일)
class _FallbackScaffold extends StatelessWidget {
  const _FallbackScaffold();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '배짱이',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppTheme.primary,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  '로딩 중…',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
