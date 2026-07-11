import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class SavingsScreen extends StatefulWidget {
  final ApiService api;
  final String? anggotaRef;
  const SavingsScreen({super.key, required this.api, this.anggotaRef});

  @override
  State<SavingsScreen> createState() => _SavingsScreenState();
}

class _SavingsScreenState extends State<SavingsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  final _anggota = TextEditingController();
  final _jumlah = TextEditingController();

  @override
  void initState() {
    super.initState();
    if (widget.anggotaRef != null) _anggota.text = widget.anggotaRef!;
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await widget.api.listSavings(anggotaRef: widget.anggotaRef ?? (_anggota.text.trim().isEmpty ? null : _anggota.text.trim()));
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

  Future<void> _deposit() async {
    final anggota = _anggota.text.trim();
    final jumlah = double.tryParse(_jumlah.text.trim()) ?? 0;
    if (anggota.isEmpty || jumlah <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Isi anggota_ref dan jumlah')));
      return;
    }
    final res = await widget.api.createSavings({'anggota_ref': anggota, 'jumlah': jumlah});
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Simpanan dicatat')));
      _jumlah.clear();
      _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${res?['detail'] ?? 'Gagal'}')));
    }
  }

  @override
  void dispose() {
    _anggota.dispose();
    _jumlah.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Simpanan',
      subtitle: 'Catat & lihat simpanan anggota',
      body: Column(children: [
        if (widget.api.isOperator)
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
            child: Column(children: [
              TextField(controller: _anggota, decoration: const InputDecoration(labelText: 'Anggota ref', border: OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _jumlah, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Jumlah', border: OutlineInputBorder())),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _deposit,
                  style: ElevatedButton.styleFrom(backgroundColor: kAccent),
                  child: const Text('Catat Setoran', style: TextStyle(color: Colors.white)),
                ),
              ),
            ]),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? ListView(children: const [EmptyState('Belum ada data simpanan')])
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final s = _items[i];
                          return Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                            child: Row(children: [
                              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${s['nama'] ?? s['anggota_ref']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                                Text('${s['periode'] ?? ''} · ${s['status'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 11)),
                              ])),
                              Text(rp(s['jumlah'] as num?), style: const TextStyle(fontWeight: FontWeight.w600)),
                            ]),
                          );
                        },
                      ),
          ),
        ),
      ]),
    );
  }
}
