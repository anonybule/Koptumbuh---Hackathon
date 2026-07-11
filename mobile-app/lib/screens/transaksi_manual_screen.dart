import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';

class TransaksiManualScreen extends StatefulWidget {
  final ApiService api;
  const TransaksiManualScreen({super.key, required this.api});

  @override
  State<TransaksiManualScreen> createState() => _TransaksiManualScreenState();
}

class _TransaksiManualScreenState extends State<TransaksiManualScreen> {
  final _customer = TextEditingController();
  final _productId = TextEditingController();
  final _qty = TextEditingController(text: '1');
  String _payment = 'Cash';
  bool _loading = false;
  String? _error;

  Future<void> _submit() async {
    setState(() { _loading = true; _error = null; });
    final qty = double.tryParse(_qty.text.trim()) ?? 0;
    if (_customer.text.trim().isEmpty || _productId.text.trim().isEmpty || qty <= 0) {
      setState(() { _loading = false; _error = 'Lengkapi pelanggan, produk, dan jumlah'; });
      return;
    }
    final res = await widget.api.createTransaction({
      'customer_name': _customer.text.trim(),
      'payment_method': _payment,
      'line_items': [
        {'produk_sample_id': _productId.text.trim(), 'quantity': qty},
      ],
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Transaksi berhasil dicatat')));
      Navigator.pop(context);
    } else if (res != null && res['_queued'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Offline — transaksi masuk antrian, akan dikirim saat online')),
      );
      Navigator.pop(context);
    } else {
      setState(() => _error = '${res?['error']?['message'] ?? res?['detail'] ?? res?['message'] ?? 'Gagal menyimpan transaksi'}');
    }
  }

  @override
  void dispose() {
    _customer.dispose();
    _productId.dispose();
    _qty.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Transaksi Manual',
      subtitle: 'Fallback tanpa WhatsApp',
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(controller: _customer, decoration: const InputDecoration(labelText: 'Nama pelanggan', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _productId, decoration: const InputDecoration(labelText: 'ID Produk (produk_sample_id)', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Jumlah', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          InputDecorator(
            decoration: const InputDecoration(labelText: 'Metode pembayaran', border: OutlineInputBorder()),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                isExpanded: true,
                value: _payment,
                items: const [
                  DropdownMenuItem(value: 'Cash', child: Text('Tunai')),
                  DropdownMenuItem(value: 'Transfer', child: Text('Transfer')),
                  DropdownMenuItem(value: 'QRIS', child: Text('QRIS')),
                ],
                onChanged: (v) => setState(() => _payment = v ?? 'Cash'),
              ),
            ),
          ),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 20),
          SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: _loading ? null : _submit,
              style: ElevatedButton.styleFrom(backgroundColor: kAccent),
              child: _loading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Simpan Transaksi', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}
