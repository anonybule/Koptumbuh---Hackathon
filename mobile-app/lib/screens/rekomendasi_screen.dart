import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class RekomendasiScreen extends StatefulWidget {
  final ApiService api;
  const RekomendasiScreen({super.key, required this.api});

  @override
  State<RekomendasiScreen> createState() => _RekomendasiScreenState();
}

class _RekomendasiScreenState extends State<RekomendasiScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _filter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await widget.api.listRecommendations(status: _filter);
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
    final res = await widget.api.patchRecommendation(id, status);
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Status → $status')));
      _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Gagal mengubah status')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Rekomendasi',
      subtitle: 'Saran AI operasional',
      showBack: false,
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Row(children: [
            _chip('Semua', null),
            _chip('NEW', 'NEW'),
            _chip('READ', 'READ'),
            _chip('ACCEPTED', 'ACCEPTED'),
            _chip('REJECTED', 'REJECTED'),
          ]),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? ListView(children: const [EmptyState('Belum ada rekomendasi')])
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final r = _items[i];
                          return Container(
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Row(children: [
                                StatusChip('${r['priority'] ?? 'LOW'}', bg: priorityBg('${r['priority']}'), fg: priorityFg('${r['priority']}')),
                                const SizedBox(width: 8),
                                StatusChip('${r['jenis'] ?? ''}'),
                                const Spacer(),
                                Text('${r['status']}', style: const TextStyle(color: kMuted, fontSize: 10)),
                              ]),
                              const SizedBox(height: 8),
                              Text('${r['judul']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                              if (r['isi'] != null) ...[
                                const SizedBox(height: 4),
                                Text('${r['isi']}', style: const TextStyle(color: kMuted, fontSize: 12)),
                              ],
                              if (widget.api.isOperator && '${r['status']}' == 'NEW') ...[
                                const SizedBox(height: 10),
                                Row(children: [
                                  TextButton(onPressed: () => _patch('${r['id']}', 'READ'), child: const Text('Baca')),
                                  TextButton(onPressed: () => _patch('${r['id']}', 'ACCEPTED'), child: const Text('Terima')),
                                  TextButton(onPressed: () => _patch('${r['id']}', 'REJECTED'), child: const Text('Tolak')),
                                ]),
                              ],
                            ]),
                          );
                        },
                      ),
          ),
        ),
      ]),
    );
  }

  Widget _chip(String label, String? value) {
    final active = _filter == value;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label, style: TextStyle(fontSize: 11, color: active ? Colors.white : kPrimary)),
        selected: active,
        selectedColor: kPrimary,
        onSelected: (_) {
          setState(() => _filter = value);
          _load();
        },
      ),
    );
  }
}
