import 'package:flutter/material.dart';

class TinjauScreen extends StatelessWidget {
  const TinjauScreen({super.key});
  static const _c = Color(0xFF075b68);

  @override
  Widget build(BuildContext context) {
    return Container(color: _c, child: SafeArea(child: Column(children: [
      _header(context),
      Expanded(child: Container(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 40),
        decoration: const BoxDecoration(color: Color(0xFFf3f5f8), borderRadius: BorderRadius.vertical(top: Radius.circular(34))),
        child: SingleChildScrollView(child: Column(children: [
          // Safety notice
          Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: const Color(0xFFf0f6d8), borderRadius: BorderRadius.circular(18)), child: Row(children: [
            const Icon(Icons.check_circle, color: Color(0xFF8dae2c), size: 20),
            const SizedBox(width: 8),
            const Expanded(child: Text('Tidak ada data resmi yang dibuat sebelum Anda menekan Simpan.', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500))),
          ])),
          const SizedBox(height: 16),
          _summaryCard(),
          const SizedBox(height: 16),
          _impactCard(),
          const SizedBox(height: 20),
          Row(children: [
            Expanded(flex: 2, child: OutlinedButton(onPressed: () => Navigator.pop(context), style: OutlinedButton.styleFrom(foregroundColor: _c, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), side: const BorderSide(color: Color(0xFFe4e8eb)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('Ubah Data', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)))),
            const SizedBox(width: 8),
            Expanded(child: OutlinedButton(onPressed: () => Navigator.pop(context), style: OutlinedButton.styleFrom(foregroundColor: _c, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), side: const BorderSide(color: Color(0xFFe4e8eb)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('Batalkan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)))),
            const SizedBox(width: 8),
            Expanded(flex: 2, child: ElevatedButton(onPressed: () {}, style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFa8c53a), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('Simpan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)))),
          ]),
        ])),
      )),
    ])));
  }

  Widget _header(BuildContext ctx) => Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), child: Row(children: [
    GestureDetector(onTap: () => Navigator.pop(ctx), child: const Text('‹', style: TextStyle(color: Colors.white, fontSize: 34))),
    const SizedBox(width: 12),
    const Expanded(child: Column(children: [
      Text('Tinjau & Konfirmasi', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
      Text('Langkah 2 dari 3', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
    ])),
    const SizedBox(width: 50),
  ]));

  Widget _summaryCard() {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.widgets, color: _c, size: 18), SizedBox(width: 8), Text('Ringkasan Transaksi', style: TextStyle(color: _c, fontSize: 18, fontWeight: FontWeight.w600))]),
      const SizedBox(height: 14),
      _row('Jenis', 'Pembelian'),
      _row('Barang', 'Pupuk Urea'),
      _row('Jumlah', '20 karung'),
      _row('Pemasok', 'Toko Makmur'),
      _row('Total', 'Rp3.500.000'),
      _row('Tanggal', '10 Juli 2026'),
    ]));
  }

  Widget _row(String label, String value) {
    return Padding(padding: const EdgeInsets.only(bottom: 8), child: Column(children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(label, style: const TextStyle(color: Color(0xFF6c747a), fontSize: 11)),
        Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF172126))),
      ]),
      const SizedBox(height: 8),
      const Divider(height: 1, color: Color(0xFFe4e8eb)),
    ]));
  }

  Widget _impactCard() {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.auto_awesome, color: _c, size: 18), SizedBox(width: 8), Text('Dampak Otomatis', style: TextStyle(color: _c, fontSize: 18, fontWeight: FontWeight.w600))]),
      const SizedBox(height: 14),
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        const Text('Stok bertambah', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        const Text('+20 karung', style: TextStyle(color: Color(0xFF246b3d), fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 10),
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        const Text('Kas berkurang', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        const Text('Rp3.500.000', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    ]));
  }
}
