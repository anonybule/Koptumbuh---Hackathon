import 'package:flutter_test/flutter_test.dart';
import 'package:koptumbuh_mobile/main.dart';

void main() {
  testWidgets('App boots to login or loading', (WidgetTester tester) async {
    await tester.pumpWidget(const KopTumbuhApp());
    await tester.pump();
    expect(find.byType(KopTumbuhApp), findsOneWidget);
  });
}
