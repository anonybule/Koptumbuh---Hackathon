import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AktivitasScreen extends StatelessWidget {
  final ApiService api;
  final Function(int)? onNavigate;
  const AktivitasScreen({super.key, required this.api, this.onNavigate});
  static const _c = Color(0xFF075b68);

  @override
  Widget build(BuildContext context) {
    return Container(color: _c, child: SafeArea(child: Column(children: [
      _header(),
      Expanded(child: Container(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 100),
        decoration: const BoxDecoration(color: Color(0xFFf3f5f8), borderRadius: BorderRadius.vertical(top: Radius.circular(34))),
        child: Column(children: [
          // Search and filter
          Row(children: [
            Expanded(child: Container(height: 48, padding: const EdgeInsets.symmetric(horizontal: 14), decoration: BoxDecoration(color: const Color(0xFFf0f2f4), border: Border.all(color: const Color(0xFFe4e8eb)), borderRadius: BorderRadius.circular(24)), child: const Row(children: [Icon(Icons.search, color: Color(0xFF93999e), size: 18), SizedBox(width: 8), Text('Cari transaksi, anggota, atau laporan', style: TextStyle(color: Color(0xFF93999e), fontSize: 12))]))),
            const SizedBox(width: 8),
            Container(width: 48, height: 48, decoration: BoxDecoration(color: const Color(0xFF075b68), borderRadius: BorderRadius.circular(24)), child: const Icon(Icons.tune, color: Colors.white, size: 20)),
          ]),
          const SizedBox(height: 20),
          const Align(alignment: Alignment.centerLeft, child: Text('Hari ini', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFF172126)))),
          const SizedBox(height: 12),
          _activityItem(Icons.swap_vert, 'Pembelian pupuk', 'TRX-20260710-018', 'Rp3.500.000', 'Berhasil', const Color(0xFFeaf7ee), const Color(0xFF246b3d)),
          _activityItem(Icons.check_circle_outline, 'Pengajuan pembelian', 'APR-20260710-004', 'Rp12.500.000', 'Menunggu', const Color(0xFFfff3d6), const Color(0xFF7a5400)),
          _activityItem(Icons.person_add, 'Anggota baru', 'AGT-00281', 'Siti Rahma', 'Terverifikasi', const Color(0xFFe8f2f4), _c),
          _activityItem(Icons.description, 'Laporan harian', 'RPT-20260710', '10 Juli 2026', 'Selesai', const Color(0xFFeaf7ee), const Color(0xFF246b3d)),
        ]),
      )),
    ])));
  }

  Widget _header() {
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), child: Row(children: [
      GestureDetector(onTap: () => onNavigate?.call(0), child: const Text('‹', style: TextStyle(color: Colors.white, fontSize: 34))),
      const SizedBox(width: 12),
      const Text('Aktivitas Koperasi', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
    ]));
  }

  Widget _activityItem(IconData icon, String title, String id, String subtitle, String status, Color bg, Color fg) {
    return Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.fromLTRB(16, 16, 16, 16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)), child: Row(children: [
      Container(width: 54, height: 54, decoration: BoxDecoration(color: const Color(0xFFe8f2f4), borderRadius: BorderRadius.circular(18)), child: Icon(icon, color: _c, size: 26)),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF172126))),
        const SizedBox(height: 4),
        Text(id, style: const TextStyle(fontSize: 10, color: Color(0xFF6c747a))),
        const SizedBox(height: 4),
        Text(subtitle, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: _c)),
      ])),
      Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6), decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(15)), child: Text(status, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: fg))),
    ]));
  }
}
