import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class MessagesScreen extends StatefulWidget {
  final ApiService api;
  const MessagesScreen({super.key, required this.api});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  Timer? _poll;
  String? _selectedId;
  Map<String, dynamic>? _detail;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 10), (_) => _load(silent: true));
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    final res = await widget.api.listMessages();
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

  Future<void> _open(String id) async {
    setState(() { _selectedId = id; _detail = null; });
    final res = await widget.api.getMessage(id);
    if (!mounted) return;
    setState(() {
      _detail = res != null && res['success'] == true
          ? Map<String, dynamic>.from(res['data'] as Map)
          : null;
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Pesan WhatsApp',
      subtitle: 'Riwayat pesan (polling 10 dtk)',
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Row(children: [
              Expanded(
                flex: 5,
                child: RefreshIndicator(
                  onRefresh: _load,
                  child: _items.isEmpty
                      ? ListView(children: const [EmptyState('Belum ada pesan')])
                      : ListView.builder(
                          padding: const EdgeInsets.all(12),
                          itemCount: _items.length,
                          itemBuilder: (_, i) {
                            final m = _items[i];
                            final selected = _selectedId == '${m['id']}';
                            return InkWell(
                              onTap: () => _open('${m['id']}'),
                              child: Container(
                                margin: const EdgeInsets.only(bottom: 8),
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: selected ? kLight : Colors.white,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                  Row(children: [
                                    StatusChip('${m['status'] ?? ''}'),
                                    const Spacer(),
                                    Text('${m['input_type'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 10)),
                                  ]),
                                  const SizedBox(height: 6),
                                  Text('${m['raw_text'] ?? '(media)'}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
                                  Text('${m['received_at'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 10)),
                                ]),
                              ),
                            );
                          },
                        ),
                ),
              ),
              if (_selectedId != null)
                Expanded(
                  flex: 5,
                  child: Container(
                    margin: const EdgeInsets.fromLTRB(0, 12, 12, 12),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                    child: _detail == null
                        ? const Center(child: CircularProgressIndicator())
                        : ListView(children: [
                            Text('Status: ${_detail!['status']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                            const SizedBox(height: 8),
                            Text('${_detail!['raw_text'] ?? '-'}', style: const TextStyle(fontSize: 13)),
                            if (_detail!['parsing'] != null) ...[
                              const Divider(height: 24),
                              const Text('Hasil AI', style: TextStyle(fontWeight: FontWeight.w600)),
                              Text('Intent: ${_detail!['parsing']['intent']}', style: const TextStyle(fontSize: 12)),
                              Text('Confidence: ${_detail!['parsing']['confidence']}', style: const TextStyle(fontSize: 12)),
                              Text('${_detail!['parsing']['payload']}', style: const TextStyle(fontSize: 11, color: kMuted)),
                            ],
                          ]),
                  ),
                ),
            ]),
    );
  }
}
