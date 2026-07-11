import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class RestockFormScreen extends StatefulWidget {
  final ApiService api;
  final String? produkId;
  final String? nama;
  const RestockFormScreen({super.key, required this.api, this.produkId, this.nama});

  @override
  State<RestockFormScreen> createState() => _RestockFormScreenState();
}

class _RestockFormScreenState extends State<RestockFormScreen> {
  late final TextEditingController _produk;
  late final TextEditingController _nama;
  final _qty = TextEditingController(text: '10');
  final _beli = TextEditingController(text: '0');
  final _jual = TextEditingController(text: '0');
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _produk = TextEditingController(text: widget.produkId ?? '');
    _nama = TextEditingController(text: widget.nama ?? '');
  }

  Future<void> _submit() async {
    setState(() { _loading = true; _error = null; });
    final qty = double.tryParse(_qty.text.trim()) ?? 0;
    final beli = double.tryParse(_beli.text.trim()) ?? 0;
    final jual = double.tryParse(_jual.text.trim()) ?? 0;
    if (_produk.text.trim().isEmpty || qty <= 0) {
      setState(() { _loading = false; _error = 'ID produk dan jumlah wajib diisi'; });
      return;
    }
    final res = await widget.api.createRestock({
      'produk_sample_id': _produk.text.trim(),
      'jumlah_masuk': qty,
      'harga_beli': beli,
      'harga_jual': jual,
      if (_nama.text.trim().isNotEmpty) 'nama_produk': _nama.text.trim(),
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Restock berhasil dicatat')));
      Navigator.pop(context);
    } else {
      setState(() => _error = '${res?['detail'] ?? 'Gagal menyimpan restock'}');
    }
  }

  @override
  void dispose() {
    _produk.dispose();
    _nama.dispose();
    _qty.dispose();
    _beli.dispose();
    _jual.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Restock Manual',
      subtitle: 'Catat barang masuk',
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(controller: _produk, decoration: const InputDecoration(labelText: 'ID Produk', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _nama, decoration: const InputDecoration(labelText: 'Nama produk (opsional)', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Jumlah masuk', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _beli, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Harga beli', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _jual, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Harga jual', border: OutlineInputBorder())),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 20),
          SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: _loading ? null : _submit,
              style: ElevatedButton.styleFrom(backgroundColor: kPrimary),
              child: _loading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Simpan Restock', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}
