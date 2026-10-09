import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Counter extends ChangeNotifier {
  int count = 0;
  void increment() {
    count++;
    notifyListeners();
  }
}

void main() => runApp(ChangeNotifierProvider(
  create: (_) => Counter(),
  child: const MaterialApp(home: CounterPage()),
));

class CounterPage extends StatelessWidget {
  const CounterPage({super.key});
  @override
  Widget build(BuildContext context) {
    final counter = context.watch<Counter>();
    return Scaffold(
      appBar: AppBar(title: const Text('Provider Counter')),
      body: Center(child: Text('Count: ${counter.count}')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.read<Counter>().increment(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
