import 'package:flutter/material.dart';

class PersetujuanScreen extends StatelessWidget {
  const PersetujuanScreen({super.key});
  static const _c = Color(0xFF075b68);

  @override
  Widget build(BuildContext context) {
    return Container(color: _c, child: SafeArea(child: Column(children: [
      _header(context),
      // Approval hero card
      Container(
        margin: const EdgeInsets.symmetric(horizontal: 29),
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(color: const Color(0xFF2f8090), borderRadius: BorderRadius.circular(26)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Diajukan oleh', style: TextStyle(color: Color(0xFFd6eaee), fontSize: 11)),
          const SizedBox(height: 6),
          const Text('Budi • Operator Koperasi', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          const Text('Rp12.500.000', style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Container(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6), decoration: BoxDecoration(color: const Color(0xFFfff3d6), borderRadius: BorderRadius.circular(15)), child: const Text('Perlu diperiksa', style: TextStyle(color: Color(0xFF7a5400), fontSize: 10, fontWeight: FontWeight.w600))),
        ]),
      ),
      const SizedBox(height: 12),
      Expanded(child: Container(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 30),
        decoration: const BoxDecoration(color: Color(0xFFf3f5f8), borderRadius: BorderRadius.vertical(top: Radius.circular(34))),
        child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // AI check
          Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [Icon(Icons.auto_awesome, color: _c, size: 18), SizedBox(width: 8), Text('Pemeriksaan AI', style: TextStyle(color: _c, fontSize: 18, fontWeight: FontWeight.w600))]),
            const SizedBox(height: 12),
            const Text('Harga 28% lebih tinggi dari rata-rata bulan ini.', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
            const SizedBox(height: 6),
            const Text('Pastikan perubahan harga atau kualitas barang telah dijelaskan.', style: TextStyle(fontSize: 11, color: Color(0xFF6c747a))),
          ])),
          const SizedBox(height: 14),
          // Summary
          Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [Icon(Icons.widgets, color: _c, size: 18), SizedBox(width: 8), Text('Ringkasan Pengajuan', style: TextStyle(color: _c, fontSize: 18, fontWeight: FontWeight.w600))]),
            const SizedBox(height: 14),
            _d('Barang', 'Pupuk Urea'),
            _d('Jumlah', '50 karung'),
            _d('Pemasok', 'CV Tani Makmur'),
            _d('Pembayaran', 'Transfer bank'),
          ])),
          const SizedBox(height: 14),
          // Decision note
          Container(height: 54, padding: const EdgeInsets.symmetric(horizontal: 17), decoration: BoxDecoration(color: Colors.white, border: Border.all(color: const Color(0xFFe4e8eb)), borderRadius: BorderRadius.circular(20)), child: const Align(alignment: Alignment.centerLeft, child: Text('Tambahkan catatan keputusan…', style: TextStyle(fontSize: 12, color: Color(0xFF6c747a))))),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(flex: 3, child: OutlinedButton(onPressed: () {}, style: OutlinedButton.styleFrom(foregroundColor: _c, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), side: const BorderSide(color: Color(0xFFe4e8eb)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('Minta Perbaikan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)))),
            const SizedBox(width: 8),
            Expanded(flex: 3, child: ElevatedButton(onPressed: () {}, style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFa8c53a), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('Setujui', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)))),
          ]),
          const SizedBox(height: 10),
          SizedBox(width: double.infinity, height: 34, child: ElevatedButton(onPressed: () {}, style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFb52626), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)), padding: EdgeInsets.zero), child: const Text('Tolak Pengajuan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)))),
        ])),
      )),
    ])));
  }

  Widget _header(BuildContext ctx) {
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), child: Row(children: [
      GestureDetector(onTap: () => Navigator.pop(ctx), child: const Text('‹', style: TextStyle(color: Colors.white, fontSize: 34))),
      const SizedBox(width: 12),
      const Expanded(child: Column(children: [
        Text('Persetujuan Pembelian', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
        Text('Pengajuan #APR-20260710-004', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
      ])),
      const SizedBox(width: 50),
    ]));
  }

  Widget _d(String label, String value) {
    return Padding(padding: const EdgeInsets.only(bottom: 8), child: Column(children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(label, style: const TextStyle(color: Color(0xFF6c747a), fontSize: 11)),
        Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 6),
      const Divider(height: 1, color: Color(0xFFe4e8eb)),
    ]));
  }
}
