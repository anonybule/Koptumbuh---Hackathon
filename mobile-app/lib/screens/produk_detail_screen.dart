import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'restock_form_screen.dart';

class ProdukDetailScreen extends StatefulWidget {
  final ApiService api;
  final String id;
  const ProdukDetailScreen({super.key, required this.api, required this.id});

  @override
  State<ProdukDetailScreen> createState() => _ProdukDetailScreenState();
}

class _ProdukDetailScreenState extends State<ProdukDetailScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final res = await widget.api.productStock(widget.id);
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
      title: 'Detail Stok',
      subtitle: widget.id,
      actions: [
        IconButton(
          onPressed: () async {
            await Navigator.push(context, MaterialPageRoute(
              builder: (_) => RestockFormScreen(api: widget.api, produkId: widget.id, nama: _data?['nama_produk']?.toString()),
            ));
            _load();
          },
          icon: const Icon(Icons.add_box_outlined, color: Colors.white),
        ),
      ],
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _data == null
              ? const EmptyState('Data stok tidak ditemukan')
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_data!['nama_produk']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        Text('Stok: ${(_data!['stok'] as num?)?.toStringAsFixed(0) ?? '0'}',
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: kPrimary)),
                        Text('Barcode: ${_data!['barcode'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text('Lokasi: ${_data!['lokasi_simpan'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                      ]),
                    ),
                    const SizedBox(height: 16),
                    const Text('Barang masuk terbaru', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    ..._mapList(_data!['recent_masuk']).map((r) => _row('${r['date']}', 'Masuk ${r['qty']}', rp(r['harga_beli'] as num?))),
                    const SizedBox(height: 16),
                    const Text('Barang keluar terbaru', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    ..._mapList(_data!['recent_keluar']).map((r) => _row('${r['date']}', 'Keluar ${r['qty']}', rp(r['total'] as num?))),
                  ],
                ),
    );
  }

  List<Map<String, dynamic>> _mapList(dynamic raw) => List<Map<String, dynamic>>.from(
        (raw as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
      );

  Widget _row(String a, String b, String c) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(b, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            Text(a, style: const TextStyle(color: kMuted, fontSize: 10)),
          ])),
          Text(c, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
        ]),
      );
}
