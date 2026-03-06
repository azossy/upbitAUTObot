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
        // 회원가입 화면에서는 절대 다른 경로로 리다이렉트하지 않음 (로그인 화면 쌓임 방지)
        final loc = state.matchedLocation;
        final path = state.uri.path;
        if (loc == '/register' || path == '/register' || path.startsWith('/register')) return null;

        final isAuthRoute = loc == '/login' || path == '/register';
        bool loggedIn = false;
        try {
          loggedIn = ref.read(authStateProvider).isLoggedIn;
        } catch (e, st) {
          debugPrint('[Router] redirect error (authState): $e $st');
          if (isAuthRoute) return null;
          return '/login';
        }
        if (!isAuthRoute && !loggedIn) return '/login';
        if (isAuthRoute && loggedIn) return '/';
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) {
            final path = state.uri.path;
            int index = 0;
            if (path.startsWith('/positions')) {
              index = 1;
            } else if (path.startsWith('/trades')) {
              index = 2;
            } else if (path.startsWith('/news')) {
              index = 3;
            } else if (path.startsWith('/my')) {
              index = 4;
            }
            final l10n = ref.read(appLocalizationsProvider);
            return Scaffold(
              body: navigationShell,
              bottomNavigationBar: NavigationBar(
                selectedIndex: index,
                onDestinationSelected: (i) {
                  switch (i) {
                    case 0:
                      context.go('/');
                      break;
                    case 1:
                      context.go('/positions');
                      break;
                    case 2:
                      context.go('/trades');
                      break;
                    case 3:
                      context.go('/news');
                      break;
                    case 4:
                      context.go('/my');
                      break;
                  }
                },
                destinations: [
                  NavigationDestination(icon: const Icon(Icons.home), label: l10n.navDashboard),
                  NavigationDestination(icon: const Icon(Icons.account_balance_wallet), label: l10n.navPositions),
                  NavigationDestination(icon: const Icon(Icons.list), label: l10n.navTrades),
                  NavigationDestination(icon: const Icon(Icons.newspaper), label: l10n.navNews),
                  NavigationDestination(icon: const Icon(Icons.person), label: l10n.navMy),
                ],
              ),
            );
          },
          branches: [
            StatefulShellBranch(routes: [
              GoRoute(path: '/', builder: (_, __) => const DashboardScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/positions', builder: (_, __) => const PositionsScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/trades', builder: (_, __) => const TradesScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/news', builder: (_, __) => const NewsScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(
                path: '/my',
                builder: (_, __) => const MyScreen(),
                routes: [
                  GoRoute(
                    path: 'settings',
                    builder: (_, __) => const SettingsScreen(),
                    routes: [
                      GoRoute(path: 'password', builder: (_, __) => const PasswordChangeScreen()),
                    ],
                  ),
                ],
              ),
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

/// 라우터가 화면을 그리지 못할 때 표시 (빈 회색 화면 방지). 테마 의존 없이 고정 색으로 그려 예외 시에도 표시.
class _FallbackScaffold extends StatelessWidget {
  const _FallbackScaffold();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  '배짱이',
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF0381FE),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  '로딩 중…',
                  style: TextStyle(
                    fontSize: 14,
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
