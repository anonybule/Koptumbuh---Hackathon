import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/outbox_service.dart';
import '../widgets/app_widgets.dart';
import 'transaksi_manual_screen.dart';
import 'members_search_screen.dart';
import 'messages_screen.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';
import 'customers_screen.dart';
import 'savings_screen.dart';
import 'deliveries_screen.dart';
import 'my_transactions_screen.dart';
import 'my_savings_screen.dart';
import 'my_loans_screen.dart';
import 'asisten_screen.dart';

class BerandaScreen extends StatefulWidget {
  final ApiService api;
  final Function(int)? onNavigate;
  final VoidCallback onLogout;
  final Map<String, dynamic>? liveSummary;

  const BerandaScreen({
    super.key,
    required this.api,
    required this.onLogout,
    this.onNavigate,
    this.liveSummary,
  });

  @override
  State<BerandaScreen> createState() => _BerandaScreenState();
}

class _BerandaScreenState extends State<BerandaScreen> {
  double _revenue = 0;
  int _txCount = 0;
  int _stockAlerts = 0;
  int _pendingRecs = 0;
  List<Map<String, dynamic>> _recent = [];
  List<Map<String, dynamic>> _lowStock = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _applySummary(widget.liveSummary);
    _fetchData();
  }

  @override
  void didUpdateWidget(covariant BerandaScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.liveSummary != null && widget.liveSummary != oldWidget.liveSummary) {
      _applySummary(widget.liveSummary);
    }
  }

  void _applySummary(Map<String, dynamic>? d) {
    if (d == null) return;
    setState(() {
      _revenue = (d['today_sales'] ?? 0).toDouble();
      _txCount = d['transaction_count'] ?? 0;
      _stockAlerts = d['stock_alerts'] ?? 0;
      _pendingRecs = d['pending_recommendations'] ?? 0;
      _recent = List<Map<String, dynamic>>.from(
        (d['recent_transactions'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
      );
      _lowStock = List<Map<String, dynamic>>.from(
        (d['low_stock_items'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
      );
      _loading = false;
    });
  }

  Future<void> _fetchData() async {
    final flush = await OutboxService(widget.api).flush();
    if (flush.ok > 0 && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${flush.ok} transaksi offline tersinkron')),
      );
    }
    final data = await widget.api.dashboardSummary();
    if (!mounted) return;
    if (data != null && data['success'] == true) {
      _applySummary(Map<String, dynamic>.from(data['data'] as Map));
    } else {
      setState(() => _loading = false);
    }
  }

  void _push(Widget w) => Navigator.push(context, MaterialPageRoute(builder: (_) => w));

  @override
  Widget build(BuildContext context) {
    return Container(
      color: kPrimary,
      child: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 12, 0),
            child: Row(children: [
              const Expanded(child: Text('KopTumbuh', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600))),
              Text(_loading ? '…' : '$_txCount tx hari ini', style: const TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
              IconButton(
                onPressed: () => _push(NotificationsScreen(api: widget.api)),
                icon: const Icon(Icons.notifications_none, color: Colors.white),
              ),
              IconButton(
                onPressed: () => _push(ProfileScreen(api: widget.api, onLogout: widget.onLogout)),
                icon: const Icon(Icons.person_outline, color: Colors.white),
              ),
            ]),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _fetchData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: Column(children: [
                  _revenueCard(),
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.fromLTRB(18, 24, 18, 100),
                    decoration: const BoxDecoration(
                      color: kBg,
                      borderRadius: BorderRadius.vertical(top: Radius.circular(34)),
                    ),
                    child: Column(children: [
                      _layanan(),
                      const SizedBox(height: 18),
                      _recentCard(),
                      if (_lowStock.isNotEmpty) ...[
                        const SizedBox(height: 18),
                        _alertsCard(),
                      ],
                    ]),
                  ),
                ]),
              ),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _revenueCard() => Container(
        margin: const EdgeInsets.symmetric(horizontal: 24),
        padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 20),
        decoration: BoxDecoration(color: const Color(0xFF2f8090), borderRadius: BorderRadius.circular(28)),
        child: Column(children: [
          const Text('Operasional Hari Ini', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 10),
          Text(_loading ? '...' : rp(_revenue), style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text('$_txCount transaksi · $_stockAlerts stok menipis · $_pendingRecs rekomendasi',
              textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFd6eaee), fontSize: 11)),
        ]),
      );

  Widget _layanan() {
    final tiles = <_Tile>[];
    if (widget.api.isOperator) {
      tiles.addAll([
        _Tile(Icons.add_circle_outline, 'Catat TX', () => _push(TransaksiManualScreen(api: widget.api))),
        _Tile(Icons.people, 'Anggota', () => _push(MembersSearchScreen(api: widget.api))),
        _Tile(Icons.chat, 'Pesan WA', () => _push(MessagesScreen(api: widget.api))),
        _Tile(Icons.person_outline, 'Pelanggan', () => _push(CustomersScreen(api: widget.api))),
        _Tile(Icons.savings_outlined, 'Simpanan', () => _push(SavingsScreen(api: widget.api))),
        _Tile(Icons.local_shipping, 'Kirim', () => _push(DeliveriesScreen(api: widget.api))),
        _Tile(Icons.smart_toy_outlined, 'Asisten', () => _push(AsistenScreen(api: widget.api))),
      ]);
    } else {
      tiles.addAll([
        _Tile(Icons.receipt_long, 'TX Saya', () => _push(MyTransactionsScreen(api: widget.api))),
        _Tile(Icons.savings, 'Simpanan', () => _push(MySavingsScreen(api: widget.api))),
        _Tile(Icons.account_balance, 'Pinjaman', () => _push(MyLoansScreen(api: widget.api))),
        _Tile(Icons.smart_toy_outlined, 'Asisten', () => _push(AsistenScreen(api: widget.api))),
        _Tile(Icons.lightbulb_outline, 'Rekomendasi', () => widget.onNavigate?.call(3)),
      ]);
    }
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.apps, color: kPrimary, size: 18),
          SizedBox(width: 8),
          Text('Layanan Utama', style: TextStyle(color: kPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 14),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: tiles.map((t) => SizedBox(
                width: 72,
                child: GestureDetector(
                  onTap: t.onTap,
                  child: Column(children: [
                    Container(
                      width: 54,
                      height: 54,
                      decoration: BoxDecoration(color: kLight, borderRadius: BorderRadius.circular(18)),
                      child: Icon(t.icon, color: kPrimary, size: 26),
                    ),
                    const SizedBox(height: 6),
                    Text(t.label, textAlign: TextAlign.center, style: const TextStyle(color: kPrimary, fontSize: 11, fontWeight: FontWeight.w500)),
                  ]),
                ),
              )).toList(),
        ),
      ]),
    );
  }

  Widget _recentCard() => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.check_circle_outline, color: kPrimary, size: 18),
            const SizedBox(width: 8),
            const Expanded(child: Text('Transaksi Terbaru', style: TextStyle(color: kPrimary, fontSize: 18, fontWeight: FontWeight.w600))),
            TextButton(onPressed: () => widget.onNavigate?.call(1), child: const Text('Lihat semua')),
          ]),
          const SizedBox(height: 8),
          if (_recent.isEmpty)
            const Text('Belum ada transaksi hari ini. Tarik untuk refresh atau catat via POS web.', style: TextStyle(color: kMuted, fontSize: 12))
          else
            ..._recent.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${t['customer'] ?? 'Umum'}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                      Text('${t['id'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 11)),
                    ])),
                    Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text(rp(t['total'] as num?), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                      StatusChip('${t['status'] ?? ''}', bg: const Color(0xFFeaf7ee), fg: const Color(0xFF246b3d)),
                    ]),
                  ]),
                )),
        ]),
      );

  Widget _alertsCard() => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Stok Menipis', style: TextStyle(color: kPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ..._lowStock.map((p) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(children: [
                  Expanded(child: Text('${p['nama_produk']}', style: const TextStyle(fontSize: 13))),
                  StatusChip('Stok ${(p['stok'] as num?)?.toStringAsFixed(0) ?? '0'}', bg: const Color(0xFFfff3d6), fg: const Color(0xFF7a5400)),
                ]),
              )),
          TextButton(onPressed: () => widget.onNavigate?.call(2), child: const Text('Ke Produk')),
        ]),
      );
}

class _Tile {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  _Tile(this.icon, this.label, this.onTap);
}
