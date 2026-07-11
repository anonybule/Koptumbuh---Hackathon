import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  final ApiService api;
  final VoidCallback onLogin;
  const LoginScreen({super.key, required this.api, required this.onLogin});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController(text: '628123456003');
  final _pass = TextEditingController(text: 'kop123');
  bool _loading = false;
  String? _error;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });
    try {
      final ok = await widget.api.login(_phone.text.trim(), _pass.text.trim());
      if (mounted) {
        if (ok) { widget.onLogin(); }
        else { setState(() => _error = 'Nomor atau kata sandi salah'); }
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Gagal terhubung ke server');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Container(
      decoration: const BoxDecoration(gradient: LinearGradient(begin: Alignment.topLeft, colors: [Color(0xFF075b68), Color(0xFF0a6b80)])),
      child: SafeArea(child: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: Column(children: [
        const SizedBox(height: 40),
        const Text('KopTumbuh', style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text('Koperasi Desa Merah Putih', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 13)),
        const Text('by JasaAI', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 11)),
        const SizedBox(height: 40),
        Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)), child: Column(children: [
          TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Nomor WhatsApp', prefixText: '+', border: OutlineInputBorder())),
          const SizedBox(height: 16),
          TextField(controller: _pass, obscureText: true, decoration: const InputDecoration(labelText: 'Kata Sandi', border: OutlineInputBorder())),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13))),
          const SizedBox(height: 20),
          SizedBox(width: double.infinity, height: 48, child: ElevatedButton(
            onPressed: _loading ? null : _login,
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF075b68), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
            child: _loading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Text('Masuk', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
          )),
        ])),
        const SizedBox(height: 16),
        const Text('Demo: 628123456003 / kop123', style: TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
      ])))),
    ));
  }

  @override
  void dispose() { _phone.dispose(); _pass.dispose(); super.dispose(); }
}
