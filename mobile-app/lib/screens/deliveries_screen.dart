import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class DeliveriesScreen extends StatefulWidget {
  final ApiService api;
  const DeliveriesScreen({super.key, required this.api});

  @override
  State<DeliveriesScreen> createState() => _DeliveriesScreenState();
}

class _DeliveriesScreenState extends State<DeliveriesScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await widget.api.listDeliveries();
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

  Future<void> _patch(String id, String status) async {
    final res = await widget.api.patchDelivery(id, status);
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Status → $status')));
      _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${res?['detail'] ?? 'Gagal'}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Pengiriman',
      subtitle: 'Update status kurir',
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _items.isEmpty
                ? ListView(children: const [EmptyState('Belum ada pengiriman')])
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final d = _items[i];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Expanded(child: Text('${d['transaksi_sample_id'] ?? d['id']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                            StatusChip('${d['status'] ?? ''}'),
                          ]),
                          const SizedBox(height: 6),
                          Text('${d['alamat'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                          Text('Tipe: ${d['tipe'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 11)),
                          const SizedBox(height: 8),
                          Wrap(spacing: 8, children: [
                            OutlinedButton(onPressed: () => _patch('${d['id']}', 'DIKIRIM'), child: const Text('Dikirim')),
                            OutlinedButton(onPressed: () => _patch('${d['id']}', 'TIBA'), child: const Text('Tiba')),
                            OutlinedButton(onPressed: () => _patch('${d['id']}', 'GAGAL'), child: const Text('Gagal')),
                          ]),
                        ]),
                      );
                    },
                  ),
      ),
    );
  }
}
