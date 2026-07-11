import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_service.dart';

/// Offline queue for POS/manual sales when the API is unreachable.
class OutboxService {
  static const _key = 'koptumbuh_tx_outbox';

  final ApiService api;

  OutboxService(this.api);

  Future<List<Map<String, dynamic>>> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final list = jsonDecode(raw) as List;
      return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _save(List<Map<String, dynamic>> items) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(items));
  }

  Future<int> pendingCount() async => (await _load()).length;

  Future<void> enqueue(Map<String, dynamic> body, {required String clientTxId}) async {
    final items = await _load();
    items.add({
      'client_tx_id': clientTxId,
      'body': body,
      'queued_at': DateTime.now().toIso8601String(),
    });
    await _save(items);
  }

  /// Flush queued sales. Returns (ok, failed) counts.
  Future<({int ok, int failed, int remaining})> flush() async {
    final items = await _load();
    if (items.isEmpty) return (ok: 0, failed: 0, remaining: 0);

    final remaining = <Map<String, dynamic>>[];
    var ok = 0;
    var failed = 0;

    for (final item in items) {
      final clientTxId = item['client_tx_id'] as String? ?? '';
      final body = Map<String, dynamic>.from(item['body'] as Map);
      body['client_tx_id'] = clientTxId;
      final res = await api.createTransaction(
        body,
        clientTxId: clientTxId,
        enqueueOnFailure: false,
      );
      if (res != null && res['success'] == true) {
        ok++;
      } else if (res != null && res['_queued'] == true) {
        remaining.add(item);
        failed++;
      } else if (res == null) {
        remaining.add(item);
        failed++;
      } else {
        // Business error (stock/price) — drop from queue to avoid infinite retry
        failed++;
      }
    }

    await _save(remaining);
    return (ok: ok, failed: failed, remaining: remaining.length);
  }
}
