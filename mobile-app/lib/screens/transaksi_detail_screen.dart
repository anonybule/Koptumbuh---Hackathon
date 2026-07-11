import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class TransaksiDetailScreen extends StatefulWidget {
  final ApiService api;
  final String id;
  const TransaksiDetailScreen({super.key, required this.api, required this.id});

  @override
  State<TransaksiDetailScreen> createState() => _TransaksiDetailScreenState();
}

class _TransaksiDetailScreenState extends State<TransaksiDetailScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final res = await widget.api.getTransaction(widget.id);
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
    return AppScaffold(
      title: 'Detail Transaksi',
      subtitle: widget.id,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _data == null
              ? const EmptyState('Transaksi tidak ditemukan')
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_data!['customer']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        Text(rp(_data!['total'] as num?), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: kPrimary)),
                        const SizedBox(height: 8),
                        Text('Pembayaran: ${_data!['payment_method'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text('Status: ${_data!['status'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text('Tanggal: ${_data!['date'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                      ]),
                    ),
                    const SizedBox(height: 16),
                    const Text('Item', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                    const SizedBox(height: 8),
                    ...List<Map<String, dynamic>>.from(
                      (_data!['line_items'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
                    ).map((item) => Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                          child: Row(children: [
                            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('${item['nama_produk'] ?? item['produk_sample_id']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                              Text('${item['quantity']} × ${rp(item['harga'] as num?)}', style: const TextStyle(color: kMuted, fontSize: 11)),
                            ])),
                            Text(rp(item['total'] as num?), style: const TextStyle(fontWeight: FontWeight.w600)),
                          ]),
                        )),
                  ],
                ),
    );
  }
}
