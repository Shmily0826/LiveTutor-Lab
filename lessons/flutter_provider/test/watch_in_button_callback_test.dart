import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tutor_flutter_lesson/main.dart';

void main() {
  testWidgets('watch in onPressed asserts; the build subscription remains valid',
      (tester) async {
    final counter = Counter();
    addTearDown(counter.dispose);
    await tester.pumpWidget(ChangeNotifierProvider.value(
      value: counter,
      child: MaterialApp(
        home: Builder(builder: (context) {
          final watched = context.watch<Counter>();
          return Scaffold(
            body: Text('Count: ${watched.count}'),
            floatingActionButton: FloatingActionButton(
              onPressed: () => context.watch<Counter>().increment(),
              child: const Icon(Icons.add),
            ),
          );
        }),
      ),
    ));

    await tester.tap(find.byType(FloatingActionButton));
    final error = tester.takeException();
    expect(error, isAssertionError);
    expect(error.toString(), contains('Tried to listen to a value exposed with provider'));
    expect(counter.count, 0);

    counter.increment();
    await tester.pump();
    expect(find.text('Count: 1'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
