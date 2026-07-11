import 'package:flutter/material.dart';

const kPrimary = Color(0xFF075b68);
const kAccent = Color(0xFFa8c53a);
const kBg = Color(0xFFf3f5f8);
const kMuted = Color(0xFF6c747a);
const kLight = Color(0xFFe8f2f4);

String rp(num? v) {
  final n = (v ?? 0).toDouble();
  final s = n.toStringAsFixed(0);
  final buf = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write('.');
    buf.write(s[i]);
  }
  return 'Rp ${buf.toString()}';
}

class AppScaffold extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget body;
  final List<Widget>? actions;
  final Widget? floatingActionButton;
  final bool showBack;

  const AppScaffold({
    super.key,
    required this.title,
    this.subtitle,
    required this.body,
    this.actions,
    this.floatingActionButton,
    this.showBack = true,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kPrimary,
      floatingActionButton: floatingActionButton,
      body: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 8, 12, 8),
            child: Row(children: [
              if (showBack)
                IconButton(
                  onPressed: () => Navigator.maybePop(context),
                  icon: const Icon(Icons.chevron_left, color: Colors.white, size: 32),
                )
              else
                const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
                  if (subtitle != null)
                    Text(subtitle!, style: const TextStyle(color: Color(0xFFcfe1e4), fontSize: 12)),
                ]),
              ),
              ...?actions,
            ]),
          ),
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: const BoxDecoration(
                color: kBg,
                borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
              ),
              child: body,
            ),
          ),
        ]),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String text;
  const EmptyState(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(text, textAlign: TextAlign.center, style: const TextStyle(color: kMuted, fontSize: 13)),
        ),
      );
}

class StatusChip extends StatelessWidget {
  final String label;
  final Color bg;
  final Color fg;
  const StatusChip(this.label, {super.key, this.bg = kLight, this.fg = kPrimary});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(14)),
        child: Text(label, style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w600)),
      );
}

Color priorityBg(String? p) {
  switch ((p ?? '').toUpperCase()) {
    case 'CRITICAL':
    case 'HIGH':
      return const Color(0xFFffe8e8);
    case 'MEDIUM':
      return const Color(0xFFfff3d6);
    default:
      return kLight;
  }
}

Color priorityFg(String? p) {
  switch ((p ?? '').toUpperCase()) {
    case 'CRITICAL':
    case 'HIGH':
      return const Color(0xFF8b1a1a);
    case 'MEDIUM':
      return const Color(0xFF7a5400);
    default:
      return kPrimary;
  }
}
