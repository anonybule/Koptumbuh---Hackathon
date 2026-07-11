import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/polling_service.dart';
import '../services/notification_service.dart';
import '../widgets/app_widgets.dart';
import 'beranda_screen.dart';
import 'transaksi_list_screen.dart';
import 'produk_list_screen.dart';
import 'rekomendasi_screen.dart';

class MainShell extends StatefulWidget {
  final ApiService api;
  final VoidCallback onLogout;
  const MainShell({super.key, required this.api, required this.onLogout});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;
  late final PollingService _polling;
  Map<String, dynamic>? _summary;

  @override
  void initState() {
    super.initState();
    _polling = PollingService(api: widget.api, notifications: NotificationService());
    _polling.onSummary = (data) {
      if (mounted) setState(() => _summary = data);
    };
    _polling.start();
    // Ensure role is loaded from profile if missing (legacy sessions)
    if (widget.api.role == null) {
      widget.api.getProfile().then((res) {
        if (res != null && res['success'] == true && mounted) {
          setState(() => widget.api.role = res['data']?['role']?.toString());
        }
      });
    }
  }

  @override
  void dispose() {
    _polling.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      BerandaScreen(
        api: widget.api,
        onLogout: widget.onLogout,
        onNavigate: (i) => setState(() => _currentIndex = i),
        liveSummary: _summary,
      ),
      TransaksiListScreen(api: widget.api),
      ProdukListScreen(api: widget.api),
      RekomendasiScreen(api: widget.api),
    ];

    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        backgroundColor: Colors.white,
        indicatorColor: kLight,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded, color: kPrimary), label: 'Beranda'),
          NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long, color: kPrimary), label: 'Transaksi'),
          NavigationDestination(icon: Icon(Icons.inventory_2_outlined), selectedIcon: Icon(Icons.inventory_2, color: kPrimary), label: 'Produk'),
          NavigationDestination(icon: Icon(Icons.lightbulb_outline), selectedIcon: Icon(Icons.lightbulb, color: kPrimary), label: 'Rekomendasi'),
        ],
      ),
    );
  }
}
