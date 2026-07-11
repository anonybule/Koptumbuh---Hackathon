import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_widgets.dart';
import 'my_transactions_screen.dart';
import 'my_savings_screen.dart';
import 'my_loans_screen.dart';
import 'messages_screen.dart';
import 'notifications_screen.dart';
import 'members_search_screen.dart';
import 'customers_screen.dart';
import 'savings_screen.dart';
import 'deliveries_screen.dart';

class ProfileScreen extends StatefulWidget {
  final ApiService api;
  final VoidCallback onLogout;
  const ProfileScreen({super.key, required this.api, required this.onLogout});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _profile;
  bool _loading = true;
  final _nama = TextEditingController();
  final _wa = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await widget.api.getProfile();
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      final d = Map<String, dynamic>.from(res['data'] as Map);
      widget.api.role = d['role']?.toString();
      _nama.text = '${d['nama'] ?? ''}';
      _wa.text = '${d['nomor_whatsapp'] ?? ''}';
      setState(() { _profile = d; _loading = false; });
    } else {
      setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    final res = await widget.api.updateProfile({
      'nama': _nama.text.trim(),
      'nomor_whatsapp': _wa.text.trim(),
    });
    if (!mounted) return;
    if (res != null && res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profil diperbarui')));
      _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${res?['detail'] ?? 'Gagal menyimpan'}')));
    }
  }

  void _push(Widget w) => Navigator.push(context, MaterialPageRoute(builder: (_) => w));

  @override
  void dispose() {
    _nama.dispose();
    _wa.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      title: 'Profil',
      subtitle: _profile?['role']?.toString() ?? widget.api.role,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                  child: Column(children: [
                    TextField(controller: _nama, decoration: const InputDecoration(labelText: 'Nama', border: OutlineInputBorder())),
                    const SizedBox(height: 10),
                    TextField(controller: _wa, decoration: const InputDecoration(labelText: 'Nomor WhatsApp', border: OutlineInputBorder())),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _save,
                        style: ElevatedButton.styleFrom(backgroundColor: kPrimary),
                        child: const Text('Simpan Profil', style: TextStyle(color: Colors.white)),
                      ),
                    ),
                    if (_profile?['koperasi'] != null) ...[
                      const Divider(height: 24),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text('${_profile!['koperasi']['nama'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      ),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text('${_profile!['koperasi']['alamat'] ?? ''}', style: const TextStyle(color: kMuted, fontSize: 12)),
                      ),
                    ],
                  ]),
                ),
                const SizedBox(height: 16),
                if (widget.api.isAnggota) ...[
                  _link(Icons.receipt_long, 'Transaksi Saya', () => _push(MyTransactionsScreen(api: widget.api))),
                  _link(Icons.savings, 'Simpanan Saya', () => _push(MySavingsScreen(api: widget.api))),
                  _link(Icons.account_balance, 'Pinjaman Saya', () => _push(MyLoansScreen(api: widget.api))),
                ],
                if (widget.api.isOperator) ...[
                  _link(Icons.chat, 'Pesan WhatsApp', () => _push(MessagesScreen(api: widget.api))),
                  _link(Icons.people, 'Cari Anggota', () => _push(MembersSearchScreen(api: widget.api))),
                  _link(Icons.person_outline, 'Pelanggan', () => _push(CustomersScreen(api: widget.api))),
                  _link(Icons.savings_outlined, 'Simpanan Anggota', () => _push(SavingsScreen(api: widget.api))),
                  _link(Icons.local_shipping, 'Pengiriman', () => _push(DeliveriesScreen(api: widget.api))),
                ],
                _link(Icons.notifications_none, 'Notifikasi', () => _push(NotificationsScreen(api: widget.api))),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: widget.onLogout,
                  icon: const Icon(Icons.logout, color: Colors.red),
                  label: const Text('Keluar', style: TextStyle(color: Colors.red)),
                ),
              ],
            ),
    );
  }

  Widget _link(IconData icon, String label, VoidCallback onTap) => ListTile(
        leading: Icon(icon, color: kPrimary),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
        trailing: const Icon(Icons.chevron_right),
        tileColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        onTap: onTap,
      );
}
