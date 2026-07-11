import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'outbox_service.dart';

class ApiService {
  static const String _accessKey = 'koptumbuh_access_token';
  static const String _refreshKey = 'koptumbuh_refresh_token';
  static const String _roleKey = 'koptumbuh_role';
  static const String _legacyTokenKey = 'koptumbuh_jwt';

  /// Android emulator → host machine. iOS simulator / desktop → localhost.
  String baseUrl = 'http://10.0.2.2:8000/api/v1';

  final FlutterSecureStorage _secure = const FlutterSecureStorage();
  late final Dio _dio;

  String? _accessToken;
  String? _refreshToken;
  String? role;
  bool _refreshing = false;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_accessToken != null && _accessToken!.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final status = error.response?.statusCode;
        final path = error.requestOptions.path;
        if (status == 401 && !path.contains('/auth/login') && !path.contains('/auth/refresh')) {
          final ok = await _tryRefresh();
          if (ok) {
            final req = error.requestOptions;
            req.headers['Authorization'] = 'Bearer $_accessToken';
            try {
              final clone = await _dio.fetch(req);
              return handler.resolve(clone);
            } catch (e) {
              return handler.next(error);
            }
          }
          await clearToken();
        }
        handler.next(error);
      },
    ));
  }

  bool get isOperator =>
      role != null &&
      role != 'ANGGOTA' &&
      {'OPERATOR', 'ADMIN', 'PEMBINA', 'KETUA', 'BENDAHARA'}.contains(role);

  bool get isAnggota => role == 'ANGGOTA';

  Future<bool> restoreSession() async {
    _accessToken = await _secure.read(key: _accessKey);
    _refreshToken = await _secure.read(key: _refreshKey);
    role = await _secure.read(key: _roleKey);

    // Migrate legacy SharedPreferences JWT if present
    if (_accessToken == null || _accessToken!.isEmpty) {
      final prefs = await SharedPreferences.getInstance();
      final legacy = prefs.getString(_legacyTokenKey);
      if (legacy != null && legacy.isNotEmpty) {
        _accessToken = legacy;
        await _secure.write(key: _accessKey, value: legacy);
        await prefs.remove(_legacyTokenKey);
      }
    }
    return _accessToken != null && _accessToken!.isNotEmpty;
  }

  Future<void> _saveTokens({
    required String access,
    String? refresh,
    String? userRole,
  }) async {
    _accessToken = access;
    await _secure.write(key: _accessKey, value: access);
    if (refresh != null) {
      _refreshToken = refresh;
      await _secure.write(key: _refreshKey, value: refresh);
    }
    if (userRole != null) {
      role = userRole;
      await _secure.write(key: _roleKey, value: userRole);
    }
  }

  Future<void> clearToken() async {
    _accessToken = null;
    _refreshToken = null;
    role = null;
    await _secure.delete(key: _accessKey);
    await _secure.delete(key: _refreshKey);
    await _secure.delete(key: _roleKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_legacyTokenKey);
  }

  Future<bool> _tryRefresh() async {
    if (_refreshing) return false;
    if (_refreshToken == null || _refreshToken!.isEmpty) return false;
    _refreshing = true;
    try {
      final res = await Dio(BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
      )).post('/auth/refresh', data: {'refresh_token': _refreshToken});
      if (res.statusCode == 200 && res.data['success'] == true) {
        final access = res.data['data']['access_token'] as String?;
        if (access != null) {
          await _saveTokens(access: access);
          return true;
        }
      }
      return false;
    } catch (_) {
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Future<bool> login(String phone, String password) async {
    try {
      final res = await _dio.post('/auth/login', data: {
        'phone': phone,
        'password': password,
      });
      if (res.statusCode == 200 && res.data['success'] == true) {
        final data = res.data['data'] as Map<String, dynamic>;
        final user = data['user'] as Map<String, dynamic>?;
        await _saveTokens(
          access: data['access_token'] as String,
          refresh: data['refresh_token'] as String?,
          userRole: user?['role'] as String?,
        );
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> get(String path, {Map<String, dynamic>? query}) async {
    try {
      final res = await _dio.get(path, queryParameters: query);
      if (res.statusCode == 200) {
        return Map<String, dynamic>.from(res.data as Map);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> post(
    String path,
    Map<String, dynamic> body, {
    Map<String, String>? headers,
  }) async {
    try {
      final res = await _dio.post(
        path,
        data: body,
        options: headers != null ? Options(headers: headers) : null,
      );
      if (res.statusCode == 200 || res.statusCode == 201) {
        return Map<String, dynamic>.from(res.data as Map);
      }
      return null;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.sendTimeout) {
        return {'_offline': true, 'success': false};
      }
      if (e.response?.data is Map) {
        return Map<String, dynamic>.from(e.response!.data as Map);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> patch(String path, Map<String, dynamic> body) async {
    try {
      final res = await _dio.patch(path, data: body);
      if (res.statusCode == 200) {
        return Map<String, dynamic>.from(res.data as Map);
      }
      return null;
    } on DioException catch (e) {
      if (e.response?.data is Map) {
        return Map<String, dynamic>.from(e.response!.data as Map);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  // ── Convenience wrappers ──────────────────────────────────────────

  Future<Map<String, dynamic>?> dashboardSummary() => get('/mobile/dashboard/summary');

  Future<Map<String, dynamic>?> listTransactions({int page = 1, String? dateFrom, String? dateTo}) =>
      get('/mobile/transactions', query: {
        'page': page,
        if (dateFrom != null) 'date_from': dateFrom,
        if (dateTo != null) 'date_to': dateTo,
      });

  Future<Map<String, dynamic>?> getTransaction(String id) => get('/mobile/transactions/$id');

  Future<Map<String, dynamic>?> createTransaction(
    Map<String, dynamic> body, {
    String? clientTxId,
    bool enqueueOnFailure = true,
  }) async {
    final id = clientTxId ??
        'MOB-${DateTime.now().millisecondsSinceEpoch}-${body.hashCode.abs()}';
    final payload = Map<String, dynamic>.from(body);
    payload['client_tx_id'] = id;
    final res = await post(
      '/mobile/transactions',
      payload,
      headers: {'Idempotency-Key': id},
    );
    if (res != null && res['success'] == true) return res;
    if (enqueueOnFailure && res != null && res['_offline'] == true) {
      final outbox = OutboxService(this);
      await outbox.enqueue(payload, clientTxId: id);
      return {'_queued': true, 'success': false, 'client_tx_id': id};
    }
    if (enqueueOnFailure && res == null) {
      final outbox = OutboxService(this);
      await outbox.enqueue(payload, clientTxId: id);
      return {'_queued': true, 'success': false, 'client_tx_id': id};
    }
    return res;
  }

  Future<Map<String, dynamic>?> listProducts({String? q, int page = 1}) =>
      get('/mobile/products', query: {'page': page, if (q != null && q.isNotEmpty) 'q': q});

  Future<Map<String, dynamic>?> productStock(String id) => get('/mobile/products/$id/stock');

  Future<Map<String, dynamic>?> createRestock(Map<String, dynamic> body) =>
      post('/mobile/restock', body);

  Future<Map<String, dynamic>?> searchMembers(String q) =>
      get('/mobile/members/search', query: {'q': q});

  Future<Map<String, dynamic>?> memberDetail(String id) => get('/mobile/members/$id');

  Future<Map<String, dynamic>?> listCustomers({int page = 1}) =>
      get('/mobile/customers', query: {'page': page});

  Future<Map<String, dynamic>?> createCustomer(Map<String, dynamic> body) =>
      post('/mobile/customers', body);

  Future<Map<String, dynamic>?> listSavings({String? anggotaRef, int page = 1}) =>
      get('/mobile/savings', query: {
        'page': page,
        if (anggotaRef != null) 'anggota_ref': anggotaRef,
      });

  Future<Map<String, dynamic>?> createSavings(Map<String, dynamic> body) =>
      post('/mobile/savings', body);

  Future<Map<String, dynamic>?> listRecommendations({String? status, int page = 1}) =>
      get('/mobile/recommendations', query: {
        'page': page,
        if (status != null) 'status': status,
      });

  Future<Map<String, dynamic>?> patchRecommendation(String id, String status) =>
      patch('/mobile/recommendations/$id/status', {'status': status});

  Future<Map<String, dynamic>?> listMessages({String? status, String? since, int page = 1}) =>
      get('/mobile/messages', query: {
        'page': page,
        if (status != null) 'status': status,
        if (since != null) 'since': since,
      });

  Future<Map<String, dynamic>?> getMessage(String id) => get('/mobile/messages/$id');

  Future<Map<String, dynamic>?> listNotifications({int page = 1}) =>
      get('/mobile/notifications', query: {'page': page});

  Future<Map<String, dynamic>?> getProfile() => get('/mobile/profile');

  Future<Map<String, dynamic>?> updateProfile(Map<String, dynamic> body) =>
      patch('/mobile/profile', body);

  Future<Map<String, dynamic>?> myTransactions({int page = 1}) =>
      get('/mobile/my-transactions', query: {'page': page});

  Future<Map<String, dynamic>?> mySavings() => get('/mobile/my-savings');

  Future<Map<String, dynamic>?> myLoans() => get('/mobile/my-loans');

  Future<Map<String, dynamic>?> listDeliveries({int page = 1}) =>
      get('/mobile/deliveries', query: {'page': page});

  Future<Map<String, dynamic>?> patchDelivery(String id, String status) =>
      patch('/mobile/deliveries/$id/status', {'status': status});

  Future<Map<String, dynamic>?> searchKnowledge(String q, {int page = 1}) =>
      get('/mobile/knowledge/search', query: {'q': q, 'page': page});
}
