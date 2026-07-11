import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._();
  factory NotificationService() => _instance;
  NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;
  int _id = 0;

  Future<void> init() async {
    if (_ready) return;
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _plugin.initialize(const InitializationSettings(android: android, iOS: ios));
    await _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    _ready = true;
  }

  Future<void> showParsedMessageAlert({String? body}) async {
    if (!_ready) await init();
    await _plugin.show(
      _id++,
      'Konfirmasi transaksi siap',
      body ?? 'Cek WhatsApp Anda untuk konfirmasi.',
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'koptumbuh_parsed',
          'Pesan AI',
          channelDescription: 'Notifikasi saat pesan WhatsApp selesai diparse',
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
    );
  }
}
