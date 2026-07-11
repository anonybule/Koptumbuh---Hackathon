import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'savings_screen.dart';

class MemberDetailScreen extends StatefulWidget {
  final ApiService api;
  final String id;
  const MemberDetailScreen({super.key, required this.api, required this.id});

  @override
  State<MemberDetailScreen> createState() => _MemberDetailScreenState();
}

class _MemberDetailScreenState extends State<MemberDetailScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final res = await widget.api.memberDetail(widget.id);
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
      title: 'Detail Anggota',
      subtitle: widget.id,
      actions: [
        if (widget.api.isOperator)
          IconButton(
            onPressed: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => SavingsScreen(api: widget.api, anggotaRef: widget.id),
            )),
            icon: const Icon(Icons.savings_outlined, color: Colors.white),
            tooltip: 'Simpanan',
          ),
      ],
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _data == null
              ? const EmptyState('Anggota tidak ditemukan')
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_data!['nama']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        Text('NIK: ${_data!['nik'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text('Status: ${_data!['status'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text('Pekerjaan: ${_data!['pekerjaan'] ?? '-'}', style: const TextStyle(color: kMuted, fontSize: 12)),
                        const SizedBox(height: 12),
                        Text('Total simpanan', style: const TextStyle(color: kMuted, fontSize: 12)),
                        Text(rp(_data!['savings_total'] as num?), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: kPrimary)),
                      ]),
                    ),
                    const SizedBox(height: 16),
                    const Text('Transaksi terkait', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    ...List<Map<String, dynamic>>.from(
                      (_data!['recent_transactions'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
                    ).map((t) => Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                          child: Row(children: [
                            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('${t['id']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                              Text('${t['date'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 10)),
                            ])),
                            Text(rp(t['total'] as num?), style: const TextStyle(fontWeight: FontWeight.w600)),
                          ]),
                        )),
                  ],
                ),
    );
  }
}
