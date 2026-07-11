import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AsistenScreen extends StatefulWidget {
  final ApiService api;
  const AsistenScreen({super.key, required this.api});
  @override
  State<AsistenScreen> createState() => _AsistenScreenState();
}

class _AsistenScreenState extends State<AsistenScreen> {
  final _controller = TextEditingController();
  final _messages = <_ChatMessage>[
    _ChatMessage(
      isUser: false,
      text: 'Halo! Tanya seputar koperasi — saya cari di basis pengetahuan.',
    ),
  ];
  bool _busy = false;

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _controller.text).trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _messages.add(_ChatMessage(isUser: true, text: text));
      _busy = true;
    });
    _controller.clear();

    String reply;
    final lower = text.toLowerCase();
    try {
      if (lower.contains('stok') || lower.contains('stock')) {
        final res = await widget.api.dashboardSummary();
        final alerts = res?['data']?['stock_alerts'] ?? 0;
        final items = (res?['data']?['low_stock_items'] as List?) ?? [];
        final names = items.take(5).map((e) => e['nama_produk'] ?? e['name'] ?? '?').join(', ');
        reply = 'Ada $alerts produk stok menipis.${names.isNotEmpty ? '\nContoh: $names' : ''}';
      } else if (lower.contains('transaksi') || lower.contains('omzet') || lower.contains('penjualan')) {
        final res = await widget.api.dashboardSummary();
        final sales = res?['data']?['today_sales'] ?? 0;
        final count = res?['data']?['transaction_count'] ?? 0;
        reply = 'Hari ini: $count transaksi, omzet Rp ${sales.toString()}.';
      } else if (lower.contains('anggota') || lower.contains('member')) {
        reply = 'Buka menu Anggota dari Beranda untuk cari anggota, atau ketik nama di pencarian anggota.';
      } else {
        final res = await widget.api.searchKnowledge(text);
        final list = (res?['data'] as List?) ?? [];
        if (list.isEmpty) {
          reply = 'Tidak menemukan artikel untuk "$text". Coba kata kunci lain, atau tanya stok/omzet.';
        } else {
          final top = list.take(3).map((e) {
            final m = Map<String, dynamic>.from(e as Map);
            final judul = m['judul'] ?? m['title'] ?? 'Artikel';
            final isi = (m['preview'] ?? m['isi'] ?? m['ringkasan'] ?? m['snippet'] ?? '').toString();
            final snip = isi.length > 160 ? '${isi.substring(0, 160)}…' : isi;
            return '• $judul\n$snip';
          }).join('\n\n');
          reply = 'Hasil pencarian:\n\n$top';
        }
      }
    } catch (_) {
      reply = 'Gagal menghubungi server. Periksa koneksi API.';
    }

    if (!mounted) return;
    setState(() {
      _messages.add(_ChatMessage(isUser: false, text: reply));
      _busy = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    const c = Color(0xFF075b68);
    return Container(
      color: c,
      child: SafeArea(
        child: Column(children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(children: [
              Text('Asisten KopTumbuh', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
              Text('Pengetahuan + ringkasan operasional', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
            ]),
          ),
          Expanded(
            child: Container(
              decoration: const BoxDecoration(
                color: Color(0xFFf3f5f8),
                borderRadius: BorderRadius.vertical(top: Radius.circular(34)),
              ),
              child: Column(children: [
                Container(
                  margin: const EdgeInsets.all(16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Row(children: [
                      Icon(Icons.auto_awesome, color: c, size: 18),
                      SizedBox(width: 8),
                      Text('Tugas Cepat', style: TextStyle(color: c, fontSize: 16, fontWeight: FontWeight.w600)),
                    ]),
                    const SizedBox(height: 12),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      _quickChip('Cek stok', () => _send('cek stok')),
                      _quickChip('Omzet hari ini', () => _send('omzet hari ini')),
                      _quickChip('Cara simpanan', () => _send('simpanan anggota')),
                      _quickChip('Cara pinjaman', () => _send('pinjaman')),
                    ]),
                  ]),
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _messages.length + (_busy ? 1 : 0),
                    itemBuilder: (ctx, i) {
                      if (i >= _messages.length) {
                        return const Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('Mencari…', style: TextStyle(color: Color(0xFF6c747a))),
                        );
                      }
                      return _messages[i];
                    },
                  ),
                ),
                Container(
                  margin: const EdgeInsets.all(12),
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  height: 58,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: const Color(0xFFe4e8eb)),
                    borderRadius: BorderRadius.circular(29),
                  ),
                  child: Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        onSubmitted: (_) => _send(),
                        decoration: const InputDecoration(
                          border: InputBorder.none,
                          hintText: 'Tanya pengetahuan atau stok…',
                          hintStyle: TextStyle(color: Color(0xFF6c747a), fontSize: 12),
                        ),
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => _send(),
                      child: Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
                        child: const Icon(Icons.send, color: Colors.white, size: 18),
                      ),
                    ),
                  ]),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _quickChip(String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(color: const Color(0xFFe8f2f4), borderRadius: BorderRadius.circular(15)),
        child: Text(label, style: const TextStyle(color: Color(0xFF075b68), fontSize: 11, fontWeight: FontWeight.w500)),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

class _ChatMessage extends StatelessWidget {
  final bool isUser;
  final String text;
  const _ChatMessage({required this.isUser, required this.text});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF075b68) : Colors.white,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(text, style: TextStyle(color: isUser ? Colors.white : const Color(0xFF172126), fontSize: 13)),
      ),
    );
  }
}
