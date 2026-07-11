import 'dart:async';
import 'api_service.dart';
import 'notification_service.dart';

typedef SummaryCallback = void Function(Map<String, dynamic> data);
typedef RecsCallback = void Function(List<Map<String, dynamic>> items);

/// Polls messages (10s), dashboard summary (30s), recommendations (60s).
class PollingService {
  final ApiService api;
  final NotificationService notifications;

  Timer? _msgTimer;
  Timer? _summaryTimer;
  Timer? _recsTimer;

  Set<String> _knownParsedIds = {};
  bool _firstMsgPoll = true;

  SummaryCallback? onSummary;
  RecsCallback? onRecommendations;
  void Function(List<Map<String, dynamic>>)? onMessages;

  PollingService({required this.api, NotificationService? notifications})
      : notifications = notifications ?? NotificationService();

  void start() {
    stop();
    _pollMessages();
    _pollSummary();
    _pollRecs();
    _msgTimer = Timer.periodic(const Duration(seconds: 10), (_) => _pollMessages());
    _summaryTimer = Timer.periodic(const Duration(seconds: 30), (_) => _pollSummary());
    _recsTimer = Timer.periodic(const Duration(seconds: 60), (_) => _pollRecs());
  }

  void stop() {
    _msgTimer?.cancel();
    _summaryTimer?.cancel();
    _recsTimer?.cancel();
    _msgTimer = null;
    _summaryTimer = null;
    _recsTimer = null;
  }

  Future<void> _pollMessages() async {
    if (!api.isOperator) return;
    final res = await api.listMessages(status: 'PARSED', page: 1);
    if (res == null || res['success'] != true) return;
    final items = List<Map<String, dynamic>>.from(
      (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
    );
    onMessages?.call(items);

    final ids = items.map((e) => '${e['id']}').toSet();
    if (!_firstMsgPoll) {
      final neu = ids.difference(_knownParsedIds);
      if (neu.isNotEmpty) {
        await notifications.showParsedMessageAlert(
          body: 'Ada ${neu.length} konfirmasi transaksi siap — cek WhatsApp Anda.',
        );
      }
    }
    _knownParsedIds = ids;
    _firstMsgPoll = false;
  }

  Future<void> _pollSummary() async {
    final res = await api.dashboardSummary();
    if (res != null && res['success'] == true && res['data'] is Map) {
      onSummary?.call(Map<String, dynamic>.from(res['data'] as Map));
    }
  }

  Future<void> _pollRecs() async {
    final res = await api.listRecommendations(status: 'NEW', page: 1);
    if (res == null || res['success'] != true) return;
    final items = List<Map<String, dynamic>>.from(
      (res['data'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)),
    );
    onRecommendations?.call(items);
  }
}
