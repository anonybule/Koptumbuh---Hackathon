import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class CustomersScreen extends StatefulWidget {
  final ApiService api;
  const CustomersScreen({super.key, required this.api});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await widget.api.listCustomers();
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

  Future<void> _add() async {
    final nama = TextEditingController();
    final wa = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tambah Pelanggan'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nama, decoration: const InputDecoration(labelText: 'Nama')),
          TextField(controller: wa, decoration: const InputDecoration(labelText: 'WhatsApp (opsional)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Simpan')),
        ],
      ),
    );
    if (ok != true || nama.text.trim().isEmpty) return;
    final res = await widget.api.createCustomer({
      'nama_pelanggan': nama.text.trim(),
      if (wa.text.trim().isNotEmpty) 'nomor_whatsapp': wa.text.trim(),
    });
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pelanggan ditambahkan')));
      _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${res?['detail'] ?? 'Gagal'}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Pelanggan',
      subtitle: 'Pelanggan walk-in',
      actions: [
        IconButton(onPressed: _add, icon: const Icon(Icons.person_add_alt_1, color: Colors.white)),
      ],
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _items.isEmpty
                ? ListView(children: const [EmptyState('Belum ada pelanggan')])
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final c = _items[i];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${c['nama_pelanggan']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                          Text('WA: ${c['nomor_whatsapp'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        ]),
                      );
                    },
                  ),
      ),
    );
  }
}
