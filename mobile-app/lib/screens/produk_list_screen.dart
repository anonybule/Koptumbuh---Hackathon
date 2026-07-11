import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'produk_detail_screen.dart';
import 'restock_form_screen.dart';

class ProdukListScreen extends StatefulWidget {
  final ApiService api;
  const ProdukListScreen({super.key, required this.api});

  @override
  State<ProdukListScreen> createState() => _ProdukListScreenState();
}

class _ProdukListScreenState extends State<ProdukListScreen> {
  final _search = TextEditingController();
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({String? q}) async {
    setState(() => _loading = true);
    final res = await widget.api.listProducts(q: q);
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

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Produk',
      subtitle: 'Stok & katalog',
      showBack: false,
      actions: [
        if (widget.api.isOperator)
          IconButton(
            onPressed: () async {
              await Navigator.push(context, MaterialPageRoute(
                builder: (_) => RestockFormScreen(api: widget.api),
              ));
              _load(q: _search.text.trim());
            },
            icon: const Icon(Icons.add_box_outlined, color: Colors.white),
            tooltip: 'Restock',
          ),
      ],
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: TextField(
            controller: _search,
            decoration: InputDecoration(
              hintText: 'Cari produk…',
              prefixIcon: const Icon(Icons.search),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
            ),
            onSubmitted: (v) => _load(q: v.trim()),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () => _load(q: _search.text.trim()),
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? ListView(children: const [EmptyState('Produk tidak ditemukan')])
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final p = _items[i];
                          final stok = (p['stok'] as num?)?.toDouble() ?? 0;
                          final low = stok < 5;
                          return InkWell(
                            onTap: widget.api.isOperator
                                ? () => Navigator.push(context, MaterialPageRoute(
                                      builder: (_) => ProdukDetailScreen(api: widget.api, id: '${p['id']}'),
                                    ))
                                : null,
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                              child: Row(children: [
                                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                  Row(children: [
                                    Flexible(child: Text('${p['nama_produk']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                                    if (low) const Text(' ⚠️', style: TextStyle(fontSize: 12)),
                                  ]),
                                  const SizedBox(height: 4),
                                  Text('Stok: ${stok.toStringAsFixed(0)} · ${rp(p['harga_jual'] as num?)}',
                                      style: TextStyle(color: low ? const Color(0xFF7a5400) : kMuted, fontSize: 12)),
                                ])),
                                if (widget.api.isOperator) const Icon(Icons.chevron_right, color: kMuted),
                              ]),
                            ),
                          );
                        },
                      ),
          ),
        ),
      ]),
    );
  }
}
