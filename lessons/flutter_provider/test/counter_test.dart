import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tutor_flutter_lesson/main.dart';

void main() {
  testWidgets('button updates the watched count', (tester) async {
    await tester.pumpWidget(ChangeNotifierProvider(
      create: (_) => Counter(),
      child: const MaterialApp(home: CounterPage()),
    ));
    expect(find.text('Count: 0'), findsOneWidget);
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pump();
    expect(find.text('Count: 1'), findsOneWidget);
  });
}
