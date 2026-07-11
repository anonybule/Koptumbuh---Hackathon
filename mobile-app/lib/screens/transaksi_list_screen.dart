import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'transaksi_detail_screen.dart';
import 'transaksi_manual_screen.dart';

class TransaksiListScreen extends StatefulWidget {
  final ApiService api;
  const TransaksiListScreen({super.key, required this.api});

  @override
  State<TransaksiListScreen> createState() => _TransaksiListScreenState();
}

class _TransaksiListScreenState extends State<TransaksiListScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    if (widget.api.isAnggota) {
      final res = await widget.api.myTransactions();
      if (!mounted) return;
      if (res != null && res['success'] == true) {
        setState(() {
          _items = List<Map<String, dynamic>>.from(
            (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
          );
          _loading = false;
        });
      } else {
        setState(() { _loading = false; _error = 'Gagal memuat transaksi'; });
      }
      return;
    }
    final res = await widget.api.listTransactions();
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      setState(() {
        _items = List<Map<String, dynamic>>.from(
          (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
        );
        _loading = false;
      });
    } else {
      setState(() { _loading = false; _error = 'Gagal memuat transaksi'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Transaksi',
      subtitle: widget.api.isAnggota ? 'Riwayat belanja saya' : 'Riwayat penjualan',
      showBack: false,
      actions: [
        if (widget.api.isOperator)
          IconButton(
            onPressed: () async {
              await Navigator.push(context, MaterialPageRoute(
                builder: (_) => TransaksiManualScreen(api: widget.api),
              ));
              _load();
            },
            icon: const Icon(Icons.add_circle_outline, color: Colors.white),
          ),
      ],
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(children: [EmptyState(_error!)])
                : _items.isEmpty
                    ? ListView(children: const [EmptyState('Belum ada transaksi. Catat via POS web atau WhatsApp YA.')])
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final t = _items[i];
                          return InkWell(
                            onTap: widget.api.isOperator
                                ? () => Navigator.push(context, MaterialPageRoute(
                                      builder: (_) => TransaksiDetailScreen(api: widget.api, id: '${t['id']}'),
                                    ))
                                : null,
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                              child: Row(children: [
                                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                  Text('${t['customer'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                  const SizedBox(height: 4),
                                  Text('${t['id']}', style: const TextStyle(color: kMuted, fontSize: 11)),
                                  if (t['date'] != null) Text('${t['date']}', style: const TextStyle(color: kMuted, fontSize: 10)),
                                ])),
                                Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                                  Text(rp(t['total'] as num?), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                                  const SizedBox(height: 4),
                                  StatusChip('${t['status'] ?? ''}', bg: const Color(0xFFeaf7ee), fg: const Color(0xFF246b3d)),
                                ]),
                              ]),
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}
