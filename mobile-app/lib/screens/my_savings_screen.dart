import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class MySavingsScreen extends StatefulWidget {
  final ApiService api;
  const MySavingsScreen({super.key, required this.api});

  @override
  State<MySavingsScreen> createState() => _MySavingsScreenState();
}

class _MySavingsScreenState extends State<MySavingsScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final res = await widget.api.mySavings();
    if (!mounted) return;
    setState(() {
      _data = res != null && res['success'] == true
          ? Map<String, dynamic>.from(res['data'] as Map)
          : null;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final items = List<Map<String, dynamic>>.from(
      (_data?['items'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
    );
    return AppScaffold(
      title: 'Simpanan Saya',
      subtitle: 'Saldo & riwayat setoran',
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                    child: Column(children: [
                      const Text('Total simpanan', style: TextStyle(color: kMuted)),
                      Text(rp(_data?['total'] as num?), style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: kPrimary)),
                    ]),
                  ),
                  const SizedBox(height: 16),
                  if (items.isEmpty) const EmptyState('Belum ada setoran'),
                  ...items.map((s) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                        child: Row(children: [
                          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${s['periode'] ?? s['id']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                            Text('${s['paid_at'] ?? s['created_at'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 10)),
                          ])),
                          Text(rp(s['jumlah'] as num?), style: const TextStyle(fontWeight: FontWeight.w600)),
                        ]),
                      )),
                ],
              ),
            ),
    );
  }
}
