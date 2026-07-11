import 'package:flutter/material.dart';

class TransaksiBaruScreen extends StatefulWidget {
  const TransaksiBaruScreen({super.key});
  @override
  State<TransaksiBaruScreen> createState() => _TransaksiBaruScreenState();
}

class _TransaksiBaruScreenState extends State<TransaksiBaruScreen> {
  String _type = 'Pembelian';

  @override
  Widget build(BuildContext context) {
    const c = Color(0xFF075b68);
    return Container(color: c, child: SafeArea(child: Column(children: [
      _header(),
      Expanded(child: Container(
        padding: const EdgeInsets.fromLTRB(18, 22, 18, 40),
        decoration: const BoxDecoration(color: Color(0xFFf3f5f8), borderRadius: BorderRadius.vertical(top: Radius.circular(34))),
        child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Lengkapi informasi utama', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Color(0xFF172126))),
          const SizedBox(height: 4),
          const Text('Anda dapat mengetik, berbicara, atau mengunggah foto nota.', style: TextStyle(fontSize: 12, color: Color(0xFF6c747a))),
          const SizedBox(height: 18),
          _typeCard(c),
          const SizedBox(height: 16),
          _detailCard(c),
          const SizedBox(height: 16),
          _uploadCard(c),
          const SizedBox(height: 24),
          SizedBox(width: double.infinity, height: 52, child: ElevatedButton(onPressed: () {}, style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFa8c53a), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)), elevation: 4), child: const Text('Lanjutkan ke Pemeriksaan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)))),
        ])),
      )),
    ])));
  }

  Widget _header() {
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), child: Row(children: [
      GestureDetector(onTap: () => Navigator.pop(context), child: const Text('‹', style: TextStyle(color: Colors.white, fontSize: 34))),
      const SizedBox(width: 12),
      const Expanded(child: Column(children: [
        Text('Transaksi Baru', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
        Text('Langkah 1 dari 3', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
      ])),
      const SizedBox(width: 50),
    ]));
  }

  Widget _typeCard(Color c) {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.swap_vert, color: Color(0xFF075b68), size: 18), SizedBox(width: 8), Text('Jenis Transaksi', style: TextStyle(color: Color(0xFF075b68), fontSize: 18, fontWeight: FontWeight.w600))]),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: GestureDetector(onTap: () => setState(() => _type = 'Pembelian'), child: Container(height: 40, decoration: BoxDecoration(color: _type == 'Pembelian' ? c : Colors.white, borderRadius: BorderRadius.circular(20), border: _type == 'Pembelian' ? null : Border.all(color: const Color(0xFFe4e8eb))), child: Center(child: Text('Pembelian', style: TextStyle(color: _type == 'Pembelian' ? Colors.white : c, fontSize: 12, fontWeight: FontWeight.w600)))))),
        const SizedBox(width: 12),
        Expanded(child: GestureDetector(onTap: () => setState(() => _type = 'Penjualan'), child: Container(height: 40, decoration: BoxDecoration(color: _type == 'Penjualan' ? c : Colors.white, borderRadius: BorderRadius.circular(20), border: _type == 'Penjualan' ? null : Border.all(color: const Color(0xFFe4e8eb))), child: Center(child: Text('Penjualan', style: TextStyle(color: _type == 'Penjualan' ? Colors.white : c, fontSize: 12, fontWeight: FontWeight.w600)))))),
      ]),
    ]));
  }

  Widget _detailCard(Color c) {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.widgets, color: Color(0xFF075b68), size: 18), SizedBox(width: 8), Text('Detail Pembelian', style: TextStyle(color: Color(0xFF075b68), fontSize: 18, fontWeight: FontWeight.w600))]),
      const SizedBox(height: 14),
      _field('Barang', 'Pupuk Urea'),
      _field('Jumlah', '20 karung'),
      _field('Pemasok', 'Toko Makmur'),
      _field('Total', 'Rp3.500.000'),
    ]));
  }

  Widget _field(String label, String value) {
    return Padding(padding: const EdgeInsets.only(bottom: 10), child: Row(children: [
      SizedBox(width: 90, child: Text(label, style: const TextStyle(color: Color(0xFF6c747a), fontSize: 11))),
      Expanded(child: Container(height: 38, padding: const EdgeInsets.symmetric(horizontal: 12), decoration: BoxDecoration(color: const Color(0xFFf7f8f9), border: Border.all(color: const Color(0xFFe4e8eb)), borderRadius: BorderRadius.circular(12)), child: Align(alignment: Alignment.centerLeft, child: Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFF172126)))))),
    ]));
  }

  Widget _uploadCard(Color c) {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.image_outlined, color: Color(0xFF075b68), size: 18), SizedBox(width: 8), Text('Bukti Transaksi', style: TextStyle(color: Color(0xFF075b68), fontSize: 18, fontWeight: FontWeight.w600))]),
      const SizedBox(height: 10),
      Container(height: 40, decoration: BoxDecoration(color: const Color(0xFFe8f2f4), borderRadius: BorderRadius.circular(15)), child: const Center(child: Text('＋  Tambah foto atau dokumen', style: TextStyle(color: Color(0xFF075b68), fontSize: 11, fontWeight: FontWeight.w600)))),
    ]));
  }
}
