import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class MyLoansScreen extends StatefulWidget {
  final ApiService api;
  const MyLoansScreen({super.key, required this.api});

  @override
  State<MyLoansScreen> createState() => _MyLoansScreenState();
}

class _MyLoansScreenState extends State<MyLoansScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final res = await widget.api.myLoans();
    if (!mounted) return;
    setState(() {
      _items = res != null && res['success'] == true
          ? List<Map<String, dynamic>>.from(
              (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
            )
          : [];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Pinjaman Saya',
      subtitle: 'Pinjaman aktif & riwayat',
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _items.isEmpty
                ? ListView(children: const [EmptyState('Belum ada pinjaman')])
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final l = _items[i];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Text(rp(l['jumlah'] as num?), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                            const Spacer(),
                            StatusChip('${l['status'] ?? ''}'),
                          ]),
                          const SizedBox(height: 6),
                          Text('Tenor ${l['tenor_bulan'] ?? '-'} bln · Bunga ${l['bunga_persen'] ?? 0}%',
                              style: const TextStyle(color: kMuted, fontSize: 12)),
                          if (l['angsuran'] != null)
                            Text('Angsuran: ${rp(l['angsuran'] as num?)}', style: const TextStyle(fontSize: 12)),
                        ]),
                      );
                    },
                  ),
      ),
    );
  }
}
