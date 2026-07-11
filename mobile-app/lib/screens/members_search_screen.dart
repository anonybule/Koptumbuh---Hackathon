import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'member_detail_screen.dart';

class MembersSearchScreen extends StatefulWidget {
  final ApiService api;
  const MembersSearchScreen({super.key, required this.api});

  @override
  State<MembersSearchScreen> createState() => _MembersSearchScreenState();
}

class _MembersSearchScreenState extends State<MembersSearchScreen> {
  final _q = TextEditingController();
  List<Map<String, dynamic>> _items = [];
  bool _loading = false;
  String? _hint = 'Cari nama atau NIK anggota';

  Future<void> _search() async {
    final q = _q.text.trim();
    if (q.isEmpty) return;
    setState(() { _loading = true; _hint = null; });
    final res = await widget.api.searchMembers(q);
    if (!mounted) return;
    setState(() {
      _items = res != null && res['success'] == true
          ? List<Map<String, dynamic>>.from(
              (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
            )
          : [];
      _loading = false;
      if (_items.isEmpty) _hint = 'Tidak ada hasil';
    });
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Anggota',
      subtitle: 'Cari anggota koperasi',
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Expanded(
              child: TextField(
                controller: _q,
                decoration: InputDecoration(
                  hintText: 'Nama atau NIK…',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                ),
                onSubmitted: (_) => _search(),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(onPressed: _search, icon: const Icon(Icons.search), style: IconButton.styleFrom(backgroundColor: kPrimary)),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _items.isEmpty
                  ? EmptyState(_hint ?? '')
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                      itemCount: _items.length,
                      itemBuilder: (_, i) {
                        final m = _items[i];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            tileColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            title: Text('${m['nama']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                            subtitle: Text('NIK ${m['nik'] ?? '-'} · ${m['status'] ?? ''}'),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () => Navigator.push(context, MaterialPageRoute(
                              builder: (_) => MemberDetailScreen(api: widget.api, id: '${m['id']}'),
                            )),
                          ),
                        );
                      },
                    ),
        ),
      ]),
    );
  }
}
