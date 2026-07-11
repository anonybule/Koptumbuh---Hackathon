import 'package:flutter/material.dart';
import 'services/api_service.dart';
import 'services/notification_service.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'widgets/app_widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService().init();
  runApp(const KopTumbuhApp());
}

class KopTumbuhApp extends StatelessWidget {
  const KopTumbuhApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KopTumbuh',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: kPrimary,
          primary: kPrimary,
          secondary: kAccent,
        ),
        scaffoldBackgroundColor: kBg,
        useMaterial3: true,
      ),
      home: const AppEntry(),
    );
  }
}

class AppEntry extends StatefulWidget {
  const AppEntry({super.key});
  @override
  State<AppEntry> createState() => _AppEntryState();
}

class _AppEntryState extends State<AppEntry> {
  final ApiService _api = ApiService();
  bool _checking = true;
  bool _loggedIn = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final hasToken = await _api.restoreSession();
    if (hasToken && _api.role == null) {
      final profile = await _api.getProfile();
      if (profile != null && profile['success'] == true) {
        _api.role = profile['data']?['role']?.toString();
      }
    }
    if (mounted) setState(() { _loggedIn = hasToken; _checking = false; });
  }

  Future<void> _onLogin() async {
    if (mounted) setState(() => _loggedIn = true);
  }

  Future<void> _onLogout() async {
    await _api.clearToken();
    if (mounted) setState(() => _loggedIn = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!_loggedIn) return LoginScreen(api: _api, onLogin: _onLogin);
    return MainShell(api: _api, onLogout: _onLogout);
  }
}
